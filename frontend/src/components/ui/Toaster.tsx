import { useState, useEffect } from 'react'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'

export interface Toast {
  id: string
  title: string
  description?: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

const toastIcons = {
  success: CheckCircle,
  error: AlertCircle, 
  warning: AlertTriangle,
  info: Info,
}

const toastStyles = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800', 
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

let toastCounter = 0
const listeners: Array<(toasts: Toast[]) => void> = []
let toastsState: Toast[] = []

const addToast = (toast: Omit<Toast, 'id'>) => {
  const id = (++toastCounter).toString()
  const newToast: Toast = { id, duration: 5000, ...toast }
  
  toastsState = [...toastsState, newToast]
  listeners.forEach(listener => listener(toastsState))
  
  // Auto remove after duration
  if (newToast.duration && newToast.duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, newToast.duration)
  }
}

const removeToast = (id: string) => {
  toastsState = toastsState.filter(toast => toast.id !== id)
  listeners.forEach(listener => listener(toastsState))
}

export const toast = {
  success: (title: string, description?: string) => addToast({ title, description, type: 'success' }),
  error: (title: string, description?: string) => addToast({ title, description, type: 'error' }),
  warning: (title: string, description?: string) => addToast({ title, description, type: 'warning' }),
  info: (title: string, description?: string) => addToast({ title, description, type: 'info' }),
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    listeners.push(setToasts)
    return () => {
      const index = listeners.indexOf(setToasts)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [])

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toastItem) => {
        const Icon = toastIcons[toastItem.type]
        return (
          <div
            key={toastItem.id}
            className={`
              max-w-sm p-4 border rounded-lg shadow-lg transition-all duration-300
              ${toastStyles[toastItem.type]}
            `}
          >
            <div className="flex items-start">
              <Icon className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{toastItem.title}</p>
                {toastItem.description && (
                  <p className="mt-1 text-sm opacity-90">{toastItem.description}</p>
                )}
              </div>
              <button
                onClick={() => removeToast(toastItem.id)}
                className="ml-3 flex-shrink-0 opacity-70 hover:opacity-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}