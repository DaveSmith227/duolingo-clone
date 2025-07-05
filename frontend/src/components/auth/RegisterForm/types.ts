import { SignUpData } from '@/lib/supabase'

export interface RegisterFormProps {
  onSuccess?: (user: any) => void
  onError?: (error: string) => void
  className?: string
  showSocialButtons?: boolean
}

export interface FormData extends SignUpData {
  confirmPassword: string
  agreeToTerms: boolean
  agreeToPrivacy: boolean
}

export interface FormErrors {
  email?: string
  firstName?: string
  password?: string
  confirmPassword?: string
  agreeToTerms?: string
  agreeToPrivacy?: string
  general?: string
}

export interface PasswordStrength {
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
}