const SLUG_MAX_LENGTH = 120;

/** The page address suggested for a title: the same characters the server accepts
 *  (Latin and Hebrew letters, digits), words joined by single hyphens. */
export function slugFromTitle(title: string): string {
  return title.toLowerCase()
    .replace(/[^a-z0-9א-ת]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, SLUG_MAX_LENGTH)
    .replace(/-+$/, "");
}
