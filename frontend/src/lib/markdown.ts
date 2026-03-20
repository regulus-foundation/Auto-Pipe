// Lightweight markdown to HTML (for server-rendered content)
// The actual markdown comes pre-rendered from the API as HTML
// This is a passthrough for dangerouslySetInnerHTML usage

export function renderMarkdown(text: string | undefined | null): string {
  if (!text) return "";
  // The FastAPI backend now returns raw markdown text.
  // We render it client-side with basic transforms.
  // For full markdown, we'll use the API endpoint.
  return text;
}
