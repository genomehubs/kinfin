/**
 * Helper to fetch all pages from a paginated REST endpoint using RTK Query's
 * `baseQuery` function. The server is expected to accept `page` and `size`
 * query params (1-based pages). The helper will fetch pages sequentially
 * until a page returns fewer than `size` items.
 *
 * Returns an object shaped like a baseQuery result: `{ data: ... }` or
 * `{ error: ... }` so it can be returned directly from `queryFn`.
 */
export async function fetchAllPages(
  baseQuery,
  {
    url,
    params = {},
    pageParam = "page",
    sizeParam = "size",
    startPage = 1,
    size = 50,
    method = "GET",
    extraParams = {},
  } = {},
) {
  try {
    let current = startPage;

    // We'll detect whether the endpoint returns an array or an object on the
    // first page and accumulate accordingly.
    let accumArray = [];
    let accumObject = {};
    let isArrayResponse = null;

    while (true) {
      const queryParams = { ...params, ...extraParams };
      queryParams[pageParam] = current;
      queryParams[sizeParam] = size;

      const res = await baseQuery({ url, method, params: queryParams });
      if (res.error) return { error: res.error };

      const payload = res.data;

      // Determine response shape
      let pageItemsArray = null;
      let pageItemsObject = null;

      if (Array.isArray(payload)) {
        pageItemsArray = payload;
      } else if (Array.isArray(payload?.data)) {
        pageItemsArray = payload.data;
      } else if (payload && typeof payload === "object") {
        // Response is an object mapping keys -> values (e.g., id -> name)
        pageItemsObject =
          payload.data && typeof payload.data === "object"
            ? payload.data
            : payload;
      }

      if (isArrayResponse === null) {
        isArrayResponse = pageItemsArray !== null;
      }

      if (isArrayResponse) {
        const items = pageItemsArray || [];
        accumArray.push(...items);
        if (items.length < size) break;
      } else {
        const itemsObj = pageItemsObject || {};
        Object.assign(accumObject, itemsObj);
        if (Object.keys(itemsObj).length < size) break;
      }

      current += 1;
    }

    if (isArrayResponse) return { data: { data: accumArray } };
    return { data: { data: accumObject } };
  } catch (err) {
    return { error: { status: "FETCH_ALL_PAGES_ERROR", data: err.message } };
  }
}

export default fetchAllPages;
