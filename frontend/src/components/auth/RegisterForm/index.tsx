'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useRegisterForm } from './useRegisterForm'
import { FormInput } from './FormInput'
import { PasswordInput } from './PasswordInput'
import { PasswordStrengthIndicator } from './PasswordStrengthIndicator'
import { ConsentCheckboxes } from './ConsentCheckboxes'
import { SubmitButton } from './SubmitButton'
import { FormErrors } from './FormErrors'
import { SocialLoginButtons } from './SocialLoginButtons'
import type { RegisterFormProps, FormData } from './types'

export function RegisterForm({ 
  onSuccess, 
  onError, 
  className = '',
  showSocialButtons = true 
}: RegisterFormProps) {
  const {
    formData,
    errors,
    isLoading,
    handleInputChange,
    handleCheckboxChange,
    handleSubmit
  } = useRegisterForm({ onSuccess, onError })

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`w-full max-w-md ${className}`}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Form Error Display */}
        {errors.general && <FormErrors error={errors.general} />}

        {/* Email Input */}
        <FormInput
          type="email"
          name="email"
          label="Email"
          value={formData.email}
          onChange={handleInputChange}
          error={errors.email}
          placeholder="Enter your email"
          autoComplete="email"
          required
        />

        {/* First Name Input */}
        <FormInput
          type="text"
          name="firstName"
          label="First Name"
          value={formData.firstName}
          onChange={handleInputChange}
          error={errors.firstName}
          placeholder="Enter your first name"
          autoComplete="given-name"
          required
        />

        {/* Password Input */}
        <PasswordInput
          name="password"
          label="Password"
          value={formData.password}
          onChange={handleInputChange}
          error={errors.password}
          showPassword={showPassword}
          onToggleVisibility={() => setShowPassword(!showPassword)}
          placeholder="Create a password"
          autoComplete="new-password"
        />

        {/* Password Strength Indicator */}
        {formData.password && (
          <PasswordStrengthIndicator password={formData.password} />
        )}

        {/* Confirm Password Input */}
        <PasswordInput
          name="confirmPassword"
          label="Confirm Password"
          value={formData.confirmPassword}
          onChange={handleInputChange}
          error={errors.confirmPassword}
          showPassword={showConfirmPassword}
          onToggleVisibility={() => setShowConfirmPassword(!showConfirmPassword)}
          placeholder="Confirm your password"
          autoComplete="new-password"
        />

        {/* Consent Checkboxes */}
        <ConsentCheckboxes
          agreeToTerms={formData.agreeToTerms}
          agreeToPrivacy={formData.agreeToPrivacy}
          onTermsChange={(checked) => handleCheckboxChange('agreeToTerms', checked)}
          onPrivacyChange={(checked) => handleCheckboxChange('agreeToPrivacy', checked)}
          termsError={errors.agreeToTerms}
          privacyError={errors.agreeToPrivacy}
        />

        {/* Submit Button */}
        <SubmitButton isLoading={isLoading} />

        {/* Social Login Buttons */}
        {showSocialButtons && (
          <>
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>
            <SocialLoginButtons disabled={isLoading} />
          </>
        )}
      </form>
    </motion.div>
  )
}

// Export types and components for external use
export type { RegisterFormProps, FormData } from './types'