/** In-app browsers (Instagram, Facebook, Android WebViews, Google app...) are refused by Google
 * sign-in with "Error 403: disallowed_useragent", so we tell the user to open a real browser. */
export function isEmbeddedBrowser(ua: string = navigator.userAgent): boolean {
  return /; wv\)|FBAN|FBAV|FB_IAB|Instagram|Line\/|MicroMessenger|GSA\/|Snapchat|TikTok/i.test(ua);
}
