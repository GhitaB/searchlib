import React from 'react';
import { Facet } from '@elastic/react-search-ui';
import {
  LeftColumnLayout,
  RightColumnLayout,
  TableRowItem,
  TableView,
} from '@eeacms/search/components';
import ListingViewItem from '@eeacms/search/components/Result/ListingViewItem';
import CardItem from '@eeacms/search/components/CardItem/CardItem';
import { Item, Card } from 'semantic-ui-react';
import {
  onResultClick,
  onAutocompleteResultClick,
  onAutocomplete,
  onSearch,
} from './lib/request';
import {
  getTermFilter,
  getRangeFilter,
} from '@eeacms/search/lib/search/filters';
import {
  getValueFacet,
  getRangeFacet,
} from '@eeacms/search/lib/search/facetValues';

export const buildRequest = (facet) => {
  return {
    [facet.field]: {
      terms: { field: facet.field, size: 100000 },
    },
  };
};

const config = {
  resolve: {
    'searchui.Facet': {
      component: Facet,
      buildRequest,
      buildFilter: getTermFilter,
      getValue: getValueFacet,
    },
    'searchui.RangeFacet': {
      component: Facet,
      buildRequest,
      buildFilter: getRangeFilter,
      getValue: getRangeFacet,
    },
    'Item.Group': {
      component: Item.Group,
    },
    'Card.Group': {
      component: (props) => (
        <Card.Group {...props} stackable itemsPerRow={4} doubling />
      ),
    },
    ListingViewItem: {
      component: ListingViewItem,
    },
    CardItem: {
      component: CardItem,
    },
    TableView: {
      component: TableView,
    },
    TableRowItem: {
      component: TableRowItem,
    },
    LeftColumnLayout: {
      component: LeftColumnLayout,
    },
    RightColumnLayout: {
      component: RightColumnLayout,
    },
  },

  searchui: {
    default: {
      host: 'http://localhost:9200',
      elastic_index: '_all',
      // debug: true,
      hasA11yNotifications: true,
      onResultClick,
      onAutocompleteResultClick,
      onAutocomplete,
      onSearch,

      // visually layout the search components (header, side, etc)
      layoutComponent: 'LeftColumnLayout',

      // when entering in search view, use this to search
      defaultSearchText: '',

      highlight: {
        fragment_size: 200,
        number_of_fragments: 1,
        fields: {},
      },

      facets: [],

      resultViews: [
        {
          id: 'listing',
          title: 'Items',
          icon: null,
          render: null,
          isDefault: true,
          factories: {
            view: 'Item.Group',
            item: 'ListingViewItem',
          },
        },
        {
          id: 'table',
          title: 'Table',
          icon: null,
          render: null,
          isDefault: false,
          factories: {
            view: 'TableView',
            item: 'TableRowItem',
          },
        },
      ],

      // parameters for the 'listing' Listing View
      // The config will lookup for `${id}ViewParams` objects
      listingViewParams: {
        enabled: true,
      },

      cardViewParams: {
        enabled: true,
      },

      tableViewParams: {
        enabled: true,
      },

      sortOptions: [
        {
          name: 'Relevance',
          value: '',
          direction: '',
        },
      ],
    },
  },
};

// if (window) {
//   window.searchUiConfig = config;
// }

export default config;
