import React from 'react'
import { motion } from 'framer-motion'
import Image from 'next/image'

interface SocialLoginButtonsProps {
  disabled?: boolean
  onGoogleLogin?: () => void
  onAppleLogin?: () => void
  onFacebookLogin?: () => void
}

export function SocialLoginButtons({ 
  disabled = false,
  onGoogleLogin,
  onAppleLogin,
  onFacebookLogin
}: SocialLoginButtonsProps) {
  const socialProviders = [
    {
      name: 'Google',
      icon: '/icons/google.svg',
      onClick: onGoogleLogin,
      bgColor: 'bg-white hover:bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-300'
    },
    {
      name: 'Apple',
      icon: '/icons/apple.svg',
      onClick: onAppleLogin,
      bgColor: 'bg-black hover:bg-gray-900',
      textColor: 'text-white',
      borderColor: 'border-black'
    },
    {
      name: 'Facebook',
      icon: '/icons/facebook.svg',
      onClick: onFacebookLogin,
      bgColor: 'bg-[#1877F2] hover:bg-[#1865F2]',
      textColor: 'text-white',
      borderColor: 'border-[#1877F2]'
    }
  ]

  return (
    <div className="space-y-3">
      {socialProviders.map((provider, index) => (
        <motion.button
          key={provider.name}
          type="button"
          onClick={provider.onClick}
          disabled={disabled}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
          className={`
            w-full flex items-center justify-center gap-3 px-4 py-3
            rounded-lg border font-medium transition-all duration-200
            ${provider.bgColor} ${provider.textColor} ${provider.borderColor}
            disabled:opacity-50 disabled:cursor-not-allowed
            focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500
          `}
        >
          <Image
            src={provider.icon}
            alt={`${provider.name} icon`}
            width={20}
            height={20}
            className="flex-shrink-0"
          />
          <span>Continue with {provider.name}</span>
        </motion.button>
      ))}
    </div>
  )
}