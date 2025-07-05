import React from 'react'
import { motion } from 'framer-motion'

interface ConsentCheckboxesProps {
  agreeToTerms: boolean
  agreeToPrivacy: boolean
  onTermsChange: (checked: boolean) => void
  onPrivacyChange: (checked: boolean) => void
  termsError?: string
  privacyError?: string
}

export function ConsentCheckboxes({
  agreeToTerms,
  agreeToPrivacy,
  onTermsChange,
  onPrivacyChange,
  termsError,
  privacyError
}: ConsentCheckboxesProps) {
  return (
    <div className="space-y-3">
      {/* Terms of Service */}
      <div>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={agreeToTerms}
            onChange={(e) => onTermsChange(e.target.checked)}
            className="mt-1 w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
            aria-invalid={!!termsError}
            aria-describedby={termsError ? 'terms-error' : undefined}
          />
          <span className="text-sm text-gray-700">
            I agree to the{' '}
            <a 
              href="/terms" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-green-600 hover:text-green-700 underline"
            >
              Terms of Service
            </a>
          </span>
        </label>
        {termsError && (
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            id="terms-error"
            className="text-sm text-red-600 mt-1 ml-6"
          >
            {termsError}
          </motion.p>
        )}
      </div>

      {/* Privacy Policy */}
      <div>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={agreeToPrivacy}
            onChange={(e) => onPrivacyChange(e.target.checked)}
            className="mt-1 w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
            aria-invalid={!!privacyError}
            aria-describedby={privacyError ? 'privacy-error' : undefined}
          />
          <span className="text-sm text-gray-700">
            I agree to the{' '}
            <a 
              href="/privacy" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-green-600 hover:text-green-700 underline"
            >
              Privacy Policy
            </a>
          </span>
        </label>
        {privacyError && (
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            id="privacy-error"
            className="text-sm text-red-600 mt-1 ml-6"
          >
            {privacyError}
          </motion.p>
        )}
      </div>
    </div>
  )
}