/**
 * Admin Feature Utility Functions
 */

/**
 * Map backend role to display-friendly format
 */
export const mapRoleForDisplay = (backendRole: string): string => {
  switch (backendRole) {
    case 'admin':
      return 'Admin'
    case 'junior_recruiter':
      return 'Junior Recruiter'
    case 'senior_recruiter':
      return 'Senior Recruiter'
    default:
      return 'Consultant'
  }
}

/**
 * Generate temporary password
 * In production, use a more secure method
 */
export const generateTempPassword = (): string => {
  return 'TempPass123!'
}