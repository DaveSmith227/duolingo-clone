export function validateEmail(email: string): string | null {
  if (!email) {
    return 'Email is required'
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email)) {
    return 'Please enter a valid email address'
  }
  
  return null
}

export function validateName(name: string): string | null {
  if (!name) {
    return 'First name is required'
  }
  
  if (name.length < 2) {
    return 'First name must be at least 2 characters'
  }
  
  if (name.length > 50) {
    return 'First name must be less than 50 characters'
  }
  
  const nameRegex = /^[a-zA-Z\s'-]+$/
  if (!nameRegex.test(name)) {
    return 'First name can only contain letters, spaces, hyphens, and apostrophes'
  }
  
  return null
}

export function validatePassword(password: string): string[] {
  const errors: string[] = []
  
  if (!password) {
    errors.push('Password is required')
    return errors
  }

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long')
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter')
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter')
  }

  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number')
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Password must contain at least one special character')
  }

  return errors
}

export function calculatePasswordStrength(password: string): {
  score: number
  label: string
  color: string
  requirements: {
    length: boolean
    uppercase: boolean
    lowercase: boolean
    number: boolean
    special: boolean
  }
} {
  const requirements = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  }

  const score = Object.values(requirements).filter(Boolean).length

  let label = 'Very Weak'
  let color = 'bg-red-500'

  if (score === 5) {
    label = 'Very Strong'
    color = 'bg-green-500'
  } else if (score === 4) {
    label = 'Strong'
    color = 'bg-green-400'
  } else if (score === 3) {
    label = 'Medium'
    color = 'bg-yellow-500'
  } else if (score === 2) {
    label = 'Weak'
    color = 'bg-orange-500'
  }

  return { score, label, color, requirements }
}