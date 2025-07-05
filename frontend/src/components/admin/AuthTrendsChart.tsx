'use client'

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

interface TimeSeriesData {
  timestamp: string
  value: number
}

interface AuthTrendsChartProps {
  loginTrends: TimeSeriesData[]
  registrationTrends: TimeSeriesData[]
  failureTrends: TimeSeriesData[]
  height?: number
}

export function AuthTrendsChart({
  loginTrends,
  registrationTrends,
  failureTrends,
  height = 300
}: AuthTrendsChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * window.devicePixelRatio
    canvas.height = rect.height * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height)

    // Calculate chart dimensions
    const padding = 40
    const chartWidth = rect.width - padding * 2
    const chartHeight = rect.height - padding * 2

    // Find min/max values
    const allValues = [
      ...loginTrends.map(d => d.value),
      ...registrationTrends.map(d => d.value),
      ...failureTrends.map(d => d.value)
    ]
    const maxValue = Math.max(...allValues)
    const minValue = 0

    // Draw grid lines
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])

    // Horizontal grid lines
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(padding + chartWidth, y)
      ctx.stroke()

      // Y-axis labels
      ctx.fillStyle = '#6b7280'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'right'
      const value = Math.round(maxValue - (maxValue / 5) * i)
      ctx.fillText(value.toString(), padding - 10, y + 4)
    }

    ctx.setLineDash([])

    // Draw lines
    const drawLine = (data: TimeSeriesData[], color: string, lineWidth: number = 2) => {
      if (data.length === 0) return

      ctx.strokeStyle = color
      ctx.lineWidth = lineWidth
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      ctx.beginPath()
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index
        const y = padding + chartHeight - ((point.value - minValue) / (maxValue - minValue)) * chartHeight

        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // Draw points
      ctx.fillStyle = color
      data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index
        const y = padding + chartHeight - ((point.value - minValue) / (maxValue - minValue)) * chartHeight
        
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fill()
      })
    }

    // Draw the lines
    drawLine(loginTrends, '#10b981') // Green for logins
    drawLine(registrationTrends, '#3b82f6') // Blue for registrations
    drawLine(failureTrends, '#ef4444') // Red for failures

    // Draw legend
    const legendItems = [
      { label: 'Successful Logins', color: '#10b981' },
      { label: 'New Registrations', color: '#3b82f6' },
      { label: 'Failed Attempts', color: '#ef4444' }
    ]

    let legendX = padding
    legendItems.forEach((item, index) => {
      const metrics = ctx.measureText(item.label)
      const itemWidth = metrics.width + 25

      // Draw legend item
      ctx.fillStyle = item.color
      ctx.fillRect(legendX, rect.height - 20, 12, 12)

      ctx.fillStyle = '#374151'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(item.label, legendX + 16, rect.height - 12)

      legendX += itemWidth + 20
    })

    // X-axis labels (dates)
    if (loginTrends.length > 0) {
      ctx.fillStyle = '#6b7280'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'center'

      const labelInterval = Math.ceil(loginTrends.length / 7) // Show max 7 labels
      loginTrends.forEach((point, index) => {
        if (index % labelInterval === 0) {
          const x = padding + (chartWidth / (loginTrends.length - 1)) * index
          const date = new Date(point.timestamp)
          const label = `${date.getMonth() + 1}/${date.getDate()}`
          ctx.fillText(label, x, rect.height - 30)
        }
      })
    }
  }, [loginTrends, registrationTrends, failureTrends])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white p-6 rounded-xl shadow-sm border border-gray-200"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Authentication Trends</h3>
      <div className="relative" style={{ height }}>
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </motion.div>
  )
}