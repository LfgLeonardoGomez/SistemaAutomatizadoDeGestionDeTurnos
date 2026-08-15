import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function Input({ label, error, id, ...props }: InputProps) {
  const inputId = id ?? props.name
  return (
    <label htmlFor={inputId} className="flex flex-col gap-1 text-left">
      <span className="text-label-md font-medium text-on-surface-variant">{label}</span>
      <input
        id={inputId}
        className={`rounded-lg border px-3 py-2 text-body-md outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/10 ${
          error ? 'border-error' : 'border-outline-variant'
        }`}
        {...props}
      />
      {error && (
        <span role="alert" className="text-label-sm text-error">
          {error}
        </span>
      )}
    </label>
  )
}
