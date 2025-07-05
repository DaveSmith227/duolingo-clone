import React from 'react'
import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { calculatePasswordStrength } from './validation'

interface PasswordStrengthIndicatorProps {
  password: string
}

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  const strength = calculatePasswordStrength(password)
  
  const requirements = [
    { key: 'length', label: 'At least 8 characters', met: strength.requirements.length },
    { key: 'uppercase', label: 'One uppercase letter', met: strength.requirements.uppercase },
    { key: 'lowercase', label: 'One lowercase letter', met: strength.requirements.lowercase },
    { key: 'number', label: 'One number', met: strength.requirements.number },
    { key: 'special', label: 'One special character', met: strength.requirements.special }
  ]

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="space-y-3"
    >
      {/* Strength Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Password strength</span>
          <span className={`font-medium ${
            strength.score >= 4 ? 'text-green-600' : 
            strength.score >= 3 ? 'text-yellow-600' : 
            'text-red-600'
          }`}>
            {strength.label}
          </span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(strength.score / 5) * 100}%` }}
            transition={{ duration: 0.3 }}
            className={`h-full ${strength.color} transition-colors duration-300`}
          />
        </div>
      </div>

      {/* Requirements List */}
      <div className="space-y-1">
        {requirements.map((req) => (
          <motion.div
            key={req.key}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-2 text-sm"
          >
            {req.met ? (
              <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
            ) : (
              <X className="w-4 h-4 text-gray-400 flex-shrink-0" />
            )}
            <span className={req.met ? 'text-green-700' : 'text-gray-500'}>
              {req.label}
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}