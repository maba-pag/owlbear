import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  label?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ''}]`, error, info.componentStack)
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children

    return (
      <div role="alert" style={{ padding: 32, textAlign: 'center' }}>
        <h3>Something went wrong{this.props.label ? ` in ${this.props.label}` : ''}</h3>
        <p style={{ color: 'var(--pds-contrast-medium)', marginBottom: 16 }}>
          {this.state.error?.message}
        </p>
        <button
          type="button"
          onClick={() => this.setState({ hasError: false, error: null })}
          style={{ cursor: 'pointer', padding: '8px 16px' }}
        >
          Try again
        </button>
      </div>
    )
  }
}
