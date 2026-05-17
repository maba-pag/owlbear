import { PButton, PHeading } from '@porsche-design-system/components-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  label?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

function syncHeadingTagAttr(element: HTMLElement | null): void {
  element?.setAttribute('tag', 'h3')
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
        <PHeading ref={syncHeadingTagAttr} tag="h3">
          Something went wrong{this.props.label ? ` in ${this.props.label}` : ''}
        </PHeading>
        <p style={{ color: 'var(--p-color-contrast-medium)', marginBottom: 16 }}>
          {this.state.error?.message}
        </p>
        <PButton
          type="button"
          onClick={() => this.setState({ hasError: false, error: null })}
          variant="secondary"
          style={{ cursor: 'pointer', padding: '8px 16px' }}
        >
          Try again
        </PButton>
      </div>
    )
  }
}
