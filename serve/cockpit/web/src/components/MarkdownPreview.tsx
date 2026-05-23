import type { ComponentProps, HTMLAttributes } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

type ReactMarkdownProps = ComponentProps<typeof ReactMarkdown>

export const MARKDOWN_PREVIEW_CLASSNAME = [
  'max-w-none leading-relaxed text-primary',
  '[&_blockquote]:my-static-sm [&_blockquote]:border-l-4 [&_blockquote]:border-contrast-low [&_blockquote]:pl-static-sm',
  '[&_code]:rounded-sm [&_code]:border [&_code]:border-contrast-low [&_code]:bg-surface [&_code]:px-1',
  '[&_h1]:mb-static-sm [&_h1]:mt-0 [&_h1]:text-xl [&_h1]:font-semibold',
  '[&_h2]:mb-static-xs [&_h2]:mt-static-sm [&_h2]:text-lg [&_h2]:font-semibold',
  '[&_h3]:mb-static-xs [&_h3]:mt-static-sm [&_h3]:text-base [&_h3]:font-semibold',
  '[&_li]:my-1 [&_li>p]:m-0',
  '[&_ol]:my-static-xs [&_ol]:list-decimal [&_ol]:pl-static-md',
  '[&_p]:my-static-xs [&_p:first-child]:mt-0 [&_p:last-child]:mb-0',
  '[&_pre]:my-static-sm [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-contrast-low [&_pre]:bg-surface [&_pre]:p-static-sm [&_pre]:shadow-sm',
  '[&_pre_code]:border-0 [&_pre_code]:bg-transparent [&_pre_code]:p-0',
  '[&_table]:my-static-sm [&_table]:w-full [&_table]:border-collapse',
  '[&_td]:border [&_td]:border-contrast-low [&_td]:p-static-xs',
  '[&_th]:border [&_th]:border-contrast-low [&_th]:p-static-xs [&_th]:text-left',
  '[&_ul]:my-static-xs [&_ul]:list-disc [&_ul]:pl-static-md',
].join(' ')

export interface MarkdownPreviewProps extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
  children: string
  remarkPlugins?: ReactMarkdownProps['remarkPlugins']
  rehypePlugins?: ReactMarkdownProps['rehypePlugins']
}

export default function MarkdownPreview({
  children,
  className = '',
  remarkPlugins = [remarkGfm],
  rehypePlugins = [rehypeSanitize],
  ...rest
}: MarkdownPreviewProps) {
  return (
    <div {...rest} className={`${className} ${MARKDOWN_PREVIEW_CLASSNAME}`.trim()}>
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
