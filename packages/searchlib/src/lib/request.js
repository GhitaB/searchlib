import { applyDisjunctiveFaceting, buildRequest, buildState } from './search';
import { default as runRequest } from './runRequest';

export function onResultClick() {
  /* Not implemented */
}

export function onAutocompleteResultClick() {
  /* Not implemented */
}

export async function onAutocomplete(props) {
  const _config = this;
  console.log('onAutocomplete', _config);
  const { searchTerm } = props;
  const resultsPerPage = 20;
  const requestBody = buildRequest({ searchTerm }, _config);
  const json = await runRequest(requestBody, _config);
  const state = buildState(json.body, resultsPerPage, _config);
  return {
    autocompletedResults: state.results,
  };
}

export async function onSearch(state) {
  const _config = this;
  console.log('onSearch', _config);
  const { resultsPerPage } = state;
  const requestBody = buildRequest(state, _config);

  // Note that this could be optimized by running all of these requests
  // at the same time. Kept simple here for clarity.
  const responseJson = await runRequest(requestBody, _config);
  const { body } = responseJson;
  const responseJsonWithDisjunctiveFacetCounts = await applyDisjunctiveFaceting(
    body,
    state,
    _config,
  );

  const newState = buildState(
    responseJsonWithDisjunctiveFacetCounts,
    resultsPerPage,
    _config,
  );
  return newState;
}
