import React from 'react'
import { motion } from 'framer-motion'
import { AlertCircle } from 'lucide-react'

interface FormErrorsProps {
  error: string
}

export function FormErrors({ error }: FormErrorsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-4 bg-red-50 border border-red-200 rounded-lg"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-red-800">{error}</p>
      </div>
    </motion.div>
  )
}