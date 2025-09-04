import { renderHook, act } from '@testing-library/react'
import { useUploadProgress } from '../../hooks/useUploadProgress'
import { DetailedProgressInfo } from '../../types'

// Mock timers
jest.useFakeTimers()

describe('useUploadProgress', () => {
  afterEach(() => {
    jest.clearAllTimers()
    jest.clearAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      expect(result.current.progressState).toEqual({
        files: new Map(),
        overallProgress: 0,
        totalFiles: 0,
        completedFiles: 0,
        failedFiles: 0,
        isUploading: false,
        startTime: 0,
        estimatedTotalTime: 0,
      })
    })

    it('should accept custom options', () => {
      const onComplete = jest.fn()
      const onError = jest.fn()
      const onProgressUpdate = jest.fn()
      
      const { result } = renderHook(() => 
        useUploadProgress({
          maxRetries: 5,
          retryDelay: 2000,
          onComplete,
          onError,
          onProgressUpdate
        })
      )
      
      // Initialize a file to test max retries
      act(() => {
        result.current.initializeProgress('test-file', 'test.pdf', 1024)
      })
      
      const fileProgress = result.current.getFileProgress('test-file')
      expect(fileProgress?.maxRetries).toBe(5)
    })
  })

  describe('file initialization', () => {
    it('should initialize progress for a new file', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      let abortController: AbortController
      
      act(() => {
        abortController = result.current.initializeProgress('file-1', 'resume.pdf', 2048)
      })
      
      expect(result.current.progressState.files.size).toBe(1)
      expect(result.current.progressState.totalFiles).toBe(1)
      expect(result.current.progressState.isUploading).toBe(true)
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress).toEqual({
        fileId: 'file-1',
        fileName: 'resume.pdf',
        stage: 'queued',
        percentage: 0,
        bytesUploaded: 0,
        totalBytes: 2048,
        timeElapsed: 0,
        estimatedTimeRemaining: 0,
        speed: 0,
        retryCount: 0,
        maxRetries: 3,
      })
      
      expect(abortController).toBeInstanceOf(AbortController)
      expect(result.current.getCancellationToken('file-1')).toBe(abortController)
    })
  })

  describe('progress updates', () => {
    it('should update file progress', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', {
          bytesUploaded: 500,
        })
      })
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.bytesUploaded).toBe(500)
      expect(fileProgress?.percentage).toBe(50)
      expect(fileProgress?.speed).toBeGreaterThan(0)
      expect(fileProgress?.estimatedTimeRemaining).toBeGreaterThan(0)
    })

    it('should calculate overall progress correctly', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume1.pdf', 1000)
        result.current.initializeProgress('file-2', 'resume2.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', { percentage: 100 })
        result.current.updateProgress('file-2', { percentage: 50 })
      })
      
      expect(result.current.progressState.overallProgress).toBe(75)
    })

    it('should track completed files', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume1.pdf', 1000)
        result.current.initializeProgress('file-2', 'resume2.pdf', 1000)
      })
      
      act(() => {
        result.current.updateStage('file-1', 'completed')
      })
      
      expect(result.current.progressState.completedFiles).toBe(1)
      expect(result.current.progressState.failedFiles).toBe(0)
    })
  })

  describe('stage updates', () => {
    it('should update file stage', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateStage('file-1', 'uploading')
      })
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('uploading')
    })
  })

  describe('cancellation', () => {
    it('should cancel single file upload', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      const abortController = result.current.getCancellationToken('file-1')
      const abortSpy = jest.spyOn(abortController!, 'abort')
      
      act(() => {
        result.current.cancelUpload('file-1')
      })
      
      expect(abortSpy).toHaveBeenCalled()
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('cancelled')
      expect(fileProgress?.percentage).toBe(0)
    })

    it('should cancel all uploads', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume1.pdf', 1000)
        result.current.initializeProgress('file-2', 'resume2.pdf', 1000)
      })
      
      const abortController1 = result.current.getCancellationToken('file-1')
      const abortController2 = result.current.getCancellationToken('file-2')
      const abortSpy1 = jest.spyOn(abortController1!, 'abort')
      const abortSpy2 = jest.spyOn(abortController2!, 'abort')
      
      act(() => {
        result.current.cancelAllUploads()
      })
      
      expect(abortSpy1).toHaveBeenCalled()
      expect(abortSpy2).toHaveBeenCalled()
      
      const fileProgress1 = result.current.getFileProgress('file-1')
      const fileProgress2 = result.current.getFileProgress('file-2')
      
      expect(fileProgress1?.stage).toBe('cancelled')
      expect(fileProgress2?.stage).toBe('cancelled')
    })
  })

  describe('retry functionality', () => {
    it('should retry failed upload', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', {
          stage: 'error',
          retryCount: 1
        })
      })
      
      let newAbortController: AbortController | null = null
      
      act(() => {
        newAbortController = result.current.retryUpload('file-1')
      })
      
      expect(newAbortController).toBeInstanceOf(AbortController)
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('queued')
      expect(fileProgress?.percentage).toBe(0)
      expect(fileProgress?.bytesUploaded).toBe(0)
      expect(fileProgress?.retryCount).toBe(2)
    })

    it('should not retry if max retries reached', () => {
      const { result } = renderHook(() => useUploadProgress({ maxRetries: 2 }))
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', {
          stage: 'error',
          retryCount: 2
        })
      })
      
      let retryResult: AbortController | null = null
      
      act(() => {
        retryResult = result.current.retryUpload('file-1')
      })
      
      expect(retryResult).toBeNull()
    })
  })

  describe('error handling', () => {
    it('should handle errors with retry logic', () => {
      const onError = jest.fn()
      const { result } = renderHook(() => useUploadProgress({ onError, maxRetries: 2 }))
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', { retryCount: 0 })
      })
      
      const error = new Error('Upload failed')
      
      act(() => {
        result.current.handleError('file-1', error)
      })
      
      // Should schedule retry
      act(() => {
        jest.advanceTimersByTime(1000)
      })
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('queued')
      expect(fileProgress?.retryCount).toBe(1)
    })

    it('should mark as error when max retries reached', () => {
      const onError = jest.fn()
      const { result } = renderHook(() => useUploadProgress({ onError, maxRetries: 1 }))
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', { retryCount: 1 })
      })
      
      const error = new Error('Upload failed')
      
      act(() => {
        result.current.handleError('file-1', error)
      })
      
      const fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('error')
      expect(onError).toHaveBeenCalledWith('file-1', error)
    })
  })

  describe('simulation', () => {
    it('should simulate progress with stages', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1024 * 1024)
      })
      
      act(() => {
        result.current.simulateProgress('file-1', 1000)
      })
      
      // Advance timers to progress through stages
      act(() => {
        jest.advanceTimersByTime(100)
      })
      
      let fileProgress = result.current.getFileProgress('file-1')
      // Should be in some active stage (uploading, validating, or extracting)
      expect(['uploading', 'validating', 'extracting'].includes(fileProgress?.stage || '')).toBe(true)
      expect(fileProgress?.percentage).toBeGreaterThan(0)
      
      // Complete the simulation
      act(() => {
        jest.advanceTimersByTime(1000)
      })
      
      fileProgress = result.current.getFileProgress('file-1')
      expect(fileProgress?.stage).toBe('completed')
      expect(fileProgress?.percentage).toBe(100)
    })
  })

  describe('time estimation', () => {
    it('should calculate time estimation correctly', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      const startTime = Date.now() - 2000 // 2 seconds ago
      const estimation = result.current.calculateTimeEstimation(500, 1000, startTime)
      
      expect(estimation.percentage).toBe(50)
      expect(estimation.speed).toBeGreaterThan(0)
      expect(estimation.remaining).toBeGreaterThan(0)
      expect(estimation.formattedRemaining).toMatch(/\d+[ms]/)
    })
  })

  describe('reset functionality', () => {
    it('should reset all progress', () => {
      const { result } = renderHook(() => useUploadProgress())
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume1.pdf', 1000)
        result.current.initializeProgress('file-2', 'resume2.pdf', 1000)
      })
      
      act(() => {
        result.current.resetProgress()
      })
      
      expect(result.current.progressState).toEqual({
        files: new Map(),
        overallProgress: 0,
        totalFiles: 0,
        completedFiles: 0,
        failedFiles: 0,
        isUploading: false,
        startTime: 0,
        estimatedTotalTime: 0,
      })
    })
  })

  describe('callbacks', () => {
    it('should call onComplete when file is completed', () => {
      const onComplete = jest.fn()
      const { result } = renderHook(() => useUploadProgress({ onComplete }))
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', { stage: 'completed' })
      })
      
      expect(onComplete).toHaveBeenCalledWith('file-1')
    })

    it('should call onProgressUpdate when progress changes', () => {
      const onProgressUpdate = jest.fn()
      const { result } = renderHook(() => useUploadProgress({ onProgressUpdate }))
      
      act(() => {
        result.current.initializeProgress('file-1', 'resume.pdf', 1000)
      })
      
      act(() => {
        result.current.updateProgress('file-1', { bytesUploaded: 500 })
      })
      
      expect(onProgressUpdate).toHaveBeenCalledWith('file-1', expect.any(Object))
    })
  })
})