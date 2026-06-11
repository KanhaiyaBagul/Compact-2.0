/**
 * Sanitizes an HTML string to mitigate Cross-Site Scripting (XSS) risks.
 * Removes script blocks, inline event handlers, javascript: URIs, and dangerous embeds.
 * @param {string} html Raw HTML
 * @returns {string} Sanitized HTML
 */
export function sanitizeHtml(html) {
  if (!html) return '';
  let clean = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  clean = clean.replace(/on\w+\s*=\s*(['"])[^'"]*?\1/gi, '');
  clean = clean.replace(/on\w+\s*=\s*[^>\s]+/gi, '');
  clean = clean.replace(/href\s*=\s*(['"])javascript:[^'"]*?\1/gi, '');
  clean = clean.replace(/<(object|embed|iframe)[^>]*>[\s\S]*?<\/\1>/gi, '');
  return clean;
}
