import React from 'react'
import { motion } from 'framer-motion'
import { Eye, EyeOff } from 'lucide-react'

interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  error?: string
  showPassword: boolean
  onToggleVisibility: () => void
}

export function PasswordInput({ 
  label, 
  error, 
  name,
  showPassword,
  onToggleVisibility,
  className = '',
  ...props 
}: PasswordInputProps) {
  return (
    <div className="space-y-1">
      <label 
        htmlFor={name} 
        className="block text-sm font-medium text-gray-700"
      >
        {label}
      </label>
      <div className="relative">
        <input
          id={name}
          name={name}
          type={showPassword ? 'text' : 'password'}
          className={`
            w-full px-4 py-3 pr-12 rounded-lg border
            ${error 
              ? 'border-red-500 focus:ring-red-500' 
              : 'border-gray-300 focus:ring-green-500'
            }
            focus:ring-2 focus:ring-offset-1 focus:border-transparent
            placeholder-gray-400 transition-colors duration-200
            ${className}
          `}
          aria-invalid={!!error}
          aria-describedby={error ? `${name}-error` : undefined}
          {...props}
        />
        <button
          type="button"
          onClick={onToggleVisibility}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-700 transition-colors"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <EyeOff className="w-5 h-5" />
          ) : (
            <Eye className="w-5 h-5" />
          )}
        </button>
      </div>
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          id={`${name}-error`}
          className="text-sm text-red-600 mt-1"
        >
          {error}
        </motion.p>
      )}
    </div>
  )
}