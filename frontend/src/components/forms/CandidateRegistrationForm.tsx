'use client'

import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { candidateApi } from '@/lib/api'
import { CandidateFormData, CandidateCreateRequest, AuthExpiredError, AuthInvalidError, NetworkError } from '@/types'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import { useToastActions } from '@/components/ui/Toast'
import { cn, isValidEmail } from '@/lib/utils'

export interface CandidateRegistrationFormProps {
  className?: string
  onSuccess?: (candidateId: string) => void
}

const CandidateRegistrationForm: React.FC<CandidateRegistrationFormProps> = ({
  className,
  onSuccess,
}) => {
  const router = useRouter()
  const { handleAuthExpired } = useAuth()
  const { showSuccess, showError } = useToastActions()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CandidateFormData>({
    mode: 'onSubmit',
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      currentCompany: '',
      currentPosition: '',
      yearsExperience: undefined,
    },
  })

  // Transform form data to API format
  const transformToApiFormat = (formData: CandidateFormData): CandidateCreateRequest => {
    return {
      first_name: formData.firstName,
      last_name: formData.lastName,
      email: formData.email || undefined,
      phone: formData.phone || undefined,
      current_company: formData.currentCompany || undefined,
      current_position: formData.currentPosition || undefined,
      years_experience: formData.yearsExperience || undefined,
    }
  }

  // Submit handler
  const onSubmit = async (data: CandidateFormData) => {
    setIsSubmitting(true)

    try {
      const apiData = transformToApiFormat(data)
      const result = await candidateApi.createCandidate(apiData)

      if (result.success && result.data?.candidate) {
        showSuccess('Candidate registered successfully!')
        reset()

        if (onSuccess) {
          onSuccess(result.data.candidate.id)
        } else {
          // Default navigation to dashboard
          router.push('/dashboard')
        }
      } else {
        const errorMessage = result.data?.error || result.error?.message || 'Failed to register candidate'
        showError(errorMessage)
      }
    } catch (error) {
      console.error('Candidate registration error:', error)

      // Handle specific auth errors like other pages do
      if (error instanceof AuthExpiredError) {
        // Token expired - redirect to login
        handleAuthExpired()
        return
      } else if (error instanceof AuthInvalidError) {
        showError('Authentication failed. Please login again.')
        handleAuthExpired()
        return
      } else if (error instanceof NetworkError) {
        showError('Network error. Please check your connection and try again.')
      } else {
        showError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    router.back()
  }

  return (
    <Card className={cn('w-full max-w-2xl mx-auto', className)}>
      <CardHeader
        title="Register New Candidate"
        subtitle="Add a new candidate to the system"
      />

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
          {/* Required Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-neutral-700 mb-1">
                First Name <span className="text-error-500">*</span>
              </label>
              <Input
                id="firstName"
                type="text"
                placeholder="Enter first name"
                disabled={isSubmitting}
                error={!!errors.firstName}
                errorMessage={errors.firstName?.message}
                {...register('firstName', {
                  required: 'First name is required',
                  minLength: {
                    value: 1,
                    message: 'First name must not be empty'
                  },
                  maxLength: {
                    value: 100,
                    message: 'First name must be 100 characters or less'
                  }
                })}
              />
            </div>

            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-neutral-700 mb-1">
                Last Name <span className="text-error-500">*</span>
              </label>
              <Input
                id="lastName"
                type="text"
                placeholder="Enter last name"
                disabled={isSubmitting}
                error={!!errors.lastName}
                errorMessage={errors.lastName?.message}
                {...register('lastName', {
                  required: 'Last name is required',
                  minLength: {
                    value: 1,
                    message: 'Last name must not be empty'
                  },
                  maxLength: {
                    value: 100,
                    message: 'Last name must be 100 characters or less'
                  }
                })}
              />
            </div>
          </div>

          {/* Optional Fields */}
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-neutral-700 mb-1">
                Email Address
              </label>
              <Input
                id="email"
                type="email"
                placeholder="Enter email address"
                disabled={isSubmitting}
                error={!!errors.email}
                errorMessage={errors.email?.message}
                {...register('email', {
                  validate: (value) => {
                    if (!value || value.trim() === '') return true // Optional field
                    if (!isValidEmail(value.trim())) {
                      return 'Please enter a valid email address'
                    }
                    return true
                  },
                })}
              />
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-neutral-700 mb-1">
                Phone Number
              </label>
              <Input
                id="phone"
                type="tel"
                placeholder="Enter phone number"
                disabled={isSubmitting}
                error={!!errors.phone}
                errorMessage={errors.phone?.message}
                {...register('phone', {
                  maxLength: {
                    value: 50,
                    message: 'Phone number must be 50 characters or less'
                  }
                })}
              />
            </div>

            <div>
              <label htmlFor="currentCompany" className="block text-sm font-medium text-neutral-700 mb-1">
                Current Company
              </label>
              <Input
                id="currentCompany"
                type="text"
                placeholder="Enter current company"
                disabled={isSubmitting}
                error={!!errors.currentCompany}
                errorMessage={errors.currentCompany?.message}
                {...register('currentCompany', {
                  maxLength: {
                    value: 255,
                    message: 'Company name must be 255 characters or less'
                  }
                })}
              />
            </div>

            <div>
              <label htmlFor="currentPosition" className="block text-sm font-medium text-neutral-700 mb-1">
                Current Position
              </label>
              <Input
                id="currentPosition"
                type="text"
                placeholder="Enter current position"
                disabled={isSubmitting}
                error={!!errors.currentPosition}
                errorMessage={errors.currentPosition?.message}
                {...register('currentPosition', {
                  maxLength: {
                    value: 255,
                    message: 'Position must be 255 characters or less'
                  }
                })}
              />
            </div>

            <div>
              <label htmlFor="yearsExperience" className="block text-sm font-medium text-neutral-700 mb-1">
                Years of Experience
              </label>
              <Input
                id="yearsExperience"
                type="number"
                placeholder="Enter years of experience"
                disabled={isSubmitting}
                error={!!errors.yearsExperience}
                errorMessage={errors.yearsExperience?.message}
                {...register('yearsExperience', {
                  valueAsNumber: true,
                  min: {
                    value: 0,
                    message: 'Years of experience must be 0 or greater'
                  },
                  max: {
                    value: 50,
                    message: 'Years of experience must be 50 or less'
                  }
                })}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-4 pt-6">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              loading={isSubmitting}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Registering...' : 'Register Candidate'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export default CandidateRegistrationForm