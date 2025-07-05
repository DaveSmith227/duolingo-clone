import { useState, useCallback } from 'react'
import { auth } from '@/lib/supabase'
import { validateEmail, validatePassword, validateName } from './validation'
import type { FormData, FormErrors, RegisterFormProps } from './types'

export function useRegisterForm({ onSuccess, onError }: Pick<RegisterFormProps, 'onSuccess' | 'onError'>) {
  const [formData, setFormData] = useState<FormData>({
    email: '',
    firstName: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false,
    agreeToPrivacy: false
  })
  
  const [errors, setErrors] = useState<FormErrors>({})
  const [isLoading, setIsLoading] = useState(false)

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    
    // Clear error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }))
    }
  }, [errors])

  const handleCheckboxChange = useCallback((name: keyof FormData, checked: boolean) => {
    setFormData(prev => ({ ...prev, [name]: checked }))
    
    // Clear error when checkbox is checked
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }))
    }
  }, [errors])

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {}

    // Email validation
    const emailError = validateEmail(formData.email)
    if (emailError) newErrors.email = emailError

    // First name validation
    const nameError = validateName(formData.firstName)
    if (nameError) newErrors.firstName = nameError

    // Password validation
    const passwordErrors = validatePassword(formData.password)
    if (passwordErrors.length > 0) {
      newErrors.password = passwordErrors[0]
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    // Terms and Privacy validation
    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = 'You must agree to the Terms of Service'
    }

    if (!formData.agreeToPrivacy) {
      newErrors.agreeToPrivacy = 'You must agree to the Privacy Policy'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }, [formData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    setErrors({})

    try {
      const { user, session, error } = await auth.signUp({
        email: formData.email,
        password: formData.password,
        firstName: formData.firstName,
        metadata: {
          agreeToTerms: formData.agreeToTerms,
          agreeToPrivacy: formData.agreeToPrivacy,
          signUpDate: new Date().toISOString()
        }
      })

      if (error) {
        throw error
      }

      if (user) {
        onSuccess?.(user)
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Registration failed. Please try again.'
      setErrors({ general: errorMessage })
      onError?.(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return {
    formData,
    errors,
    isLoading,
    handleInputChange,
    handleCheckboxChange,
    handleSubmit
  }
}