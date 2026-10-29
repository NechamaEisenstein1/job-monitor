export const ARTICLES_PATH = "/articles";
export const ADMIN_ARTICLES_PATH = "/admin/articles";

export const articlePath = (slug: string) => `${ARTICLES_PATH}/${encodeURIComponent(slug)}`;
export const articleEditorPath = (id: number) => `${ADMIN_ARTICLES_PATH}/${id}`;
export const newArticlePath = `${ADMIN_ARTICLES_PATH}/new`;
