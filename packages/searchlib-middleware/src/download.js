const es = require('elasticsearch');
const stringify = require('csv-stringify');

const SCROLL_TIME = '5m';
const SCROLL_SIZE = 2000;

const download = (es_config, req, res, appConfig) => {
  console.log(appConfig);

  const es_url = new URL(es_config);
  const es_path_parts = es_url.pathname.split('/');

  const es_index = es_path_parts.pop();
  es_url.pathname = es_path_parts.join();

  const es_host = es_url.href;

  /*TODO*/
  const download_mapping = [];
  /*TODO*/

  const dataQueryStr = req.query.download_query.split('?source=')[1];
  const dataQuery = JSON.parse(dataQueryStr);

  const linebreak = '\n';
  const delimiter = ',';

  const stringifier = stringify({ delimiter: delimiter });

  res.setHeader('Content-Encoding', 'UTF-8');
  res.setHeader('Content-Type', 'text/csv;charset=UTF-8');
  res.setHeader('Content-disposition', 'attachment; filename=data.csv');
  res.write('\uFEFF');
  res.once('close', function () {
    res.end();
  });

  var csv_header = [];
  for (var i = 0; i < download_mapping.length; i++) {
    csv_header.push(download_mapping[i].name);
  }

  res.write(stringifier.stringify(csv_header));
  res.write(linebreak);

  const client = new es.Client({
    host: es_host,
    type: 'stdio',
    levels: ['error'],
  });

  var offset = 0;
  dataQuery.size = SCROLL_SIZE;
  client.search(
    {
      index: es_index,
      scroll: SCROLL_TIME, // keep the search results "scrollable" for the time specified in SCROLL_TIME constant
      body: dataQuery,
    },
    function getMoreUntilDone(error, data) {
      if (error || data === undefined || data.hits === undefined) {
        if (error) {
          console.log('Error while downloading:', error);
        } else {
          console.log('Error in data while downloading:', data);
        }
        res.destroy();
        return;
      }
      if (res.finished) {
        return;
      }
      let total = 0;
      total = data.hits.total.value;
      if (total > offset) {
        var chunk = '';
        for (var i = 0; i < data.hits.hits.length; i++) {
          const row = data.hits.hits[i];
          let csv_row = [];
          for (var j = 0; j < download_mapping.length; j++) {
            let value = row['_source'][download_mapping[j].field];
            if (value === undefined) {
              value = '';
            }
            if (!Array.isArray(value)) {
              value = [value];
            }
            const field_whitelist = download_mapping[j].values_whitelist;
            if (field_whitelist !== undefined) {
              var new_value = [];
              for (
                let value_count = 0;
                value_count < value.length;
                value_count++
              ) {
                if (field_whitelist.indexOf(value[value_count]) !== -1) {
                  new_value.push(value[value_count]);
                }
              }
              value = new_value;
            }

            var field_blacklist = download_mapping[j].values_blacklist;
            if (field_blacklist !== undefined) {
              let new_value = [];
              for (
                let value_count = 0;
                value_count < value.length;
                value_count++
              ) {
                if (field_blacklist.indexOf(value[value_count]) === -1) {
                  new_value.push(value[value_count]);
                }
              }
              value = new_value;
            }

            csv_row.push(value.toString());
          }
          chunk += stringifier.stringify(csv_row);
          chunk += linebreak;
        }
        let write_res = res.write(chunk);

        // ask elasticsearch for the next set of hits from this search
        offset += SCROLL_SIZE;
        if (!write_res) {
          res.once('drain', function () {
            client.scroll(
              {
                scroll: SCROLL_TIME,
                scrollId: data._scroll_id,
              },
              getMoreUntilDone,
            );
          });
        } else {
          client.scroll(
            {
              scroll: SCROLL_TIME,
              scrollId: data._scroll_id,
            },
            getMoreUntilDone,
          );
        }
      } else {
        res.end();
      }
    },
  );
};

export default download;
