/// <reference types="vite/client" />

declare namespace React {
  namespace JSX {
    interface IntrinsicElements {
      'p-tabs': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement>
      'p-tabs-item': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        label?: string
      }
      'p-icon': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        name?: string
      }
    }
  }
}

