// Small reusable helpers extracted from ChartPageShell

export function getEffectiveColumnDescriptions(
  propDescriptions,
  fetchedDescriptions,
) {
  return propDescriptions && propDescriptions.length
    ? propDescriptions
    : fetchedDescriptions;
}

export function getSelectedAttributeTaxonset(
  selectedFromStore,
  initialAttribute,
  initialTaxonset,
) {
  const attribute = initialAttribute ?? selectedFromStore?.attribute ?? "all";
  const taxonset = initialTaxonset ?? selectedFromStore?.taxonset ?? "all";
  return { attribute, taxonset };
}

export function makeSetSelectedAttributeTaxonset(
  dispatch,
  propSetter,
  actionCreator,
) {
  if (propSetter) return propSetter;
  return (payload) => dispatch(actionCreator(payload));
}
