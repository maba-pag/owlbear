import { PButton, PHeading } from '@porsche-design-system/components-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'
import './ErrorBoundary.css'

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
      <div role="alert" className="error-boundary">
        <PHeading ref={syncHeadingTagAttr} tag="h3">
          Something went wrong{this.props.label ? ` in ${this.props.label}` : ''}
        </PHeading>
        <p className="error-boundary-message">
          {this.state.error?.message}
        </p>
        <PButton
          type="button"
          onClick={() => this.setState({ hasError: false, error: null })}
          variant="secondary"
          className="error-boundary-reset"
        >
          Try again
        </PButton>
      </div>
    )
  }
}
