export const updatePaginationParams = (
  searchParams,
  setSearchParams,
  prefix,
  page,
  pageSize
) => {
  const newParams = new URLSearchParams(searchParams);
  if (
    newParams.get(`${prefix}_page`) === (page + 1).toString() &&
    newParams.get(`${prefix}_pageSize`) === pageSize.toString()
  ) {
    return; // No change needed
  }
  newParams.set(`${prefix}_page`, (page + 1).toString());
  newParams.set(`${prefix}_pageSize`, pageSize.toString());
  setSearchParams(newParams, { replace: true });
};
