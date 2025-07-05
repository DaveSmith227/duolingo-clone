import React from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

interface SubmitButtonProps {
  isLoading: boolean
  loadingText?: string
  children?: React.ReactNode
}

export function SubmitButton({ 
  isLoading, 
  loadingText = 'Creating account...',
  children = 'Create Account'
}: SubmitButtonProps) {
  return (
    <motion.button
      type="submit"
      disabled={isLoading}
      whileHover={!isLoading ? { scale: 1.02 } : undefined}
      whileTap={!isLoading ? { scale: 0.98 } : undefined}
      className={`
        w-full py-3 px-4 rounded-full font-semibold text-white
        transition-all duration-200 focus:outline-none focus:ring-2 
        focus:ring-offset-2 focus:ring-green-500
        ${isLoading 
          ? 'bg-gray-400 cursor-not-allowed' 
          : 'bg-green-500 hover:bg-green-600 active:bg-green-700'
        }
      `}
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          {loadingText}
        </span>
      ) : (
        children
      )}
    </motion.button>
  )
}