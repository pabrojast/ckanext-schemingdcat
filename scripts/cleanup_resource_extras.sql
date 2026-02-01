-- Cleanup oversized resource extras created by metadata extraction.
--
-- Usage (dry run):
--   psql "$CKAN_SQLALCHEMY_URL" -f scripts/cleanup_resource_extras.sql
--
-- Usage (apply):
--   psql "$CKAN_SQLALCHEMY_URL" -v apply=1 -f scripts/cleanup_resource_extras.sql
--
-- Optional overrides:
--   -v max_bytes=50000          -- size threshold per field (0 disables size pruning)
--   -v prune_by_size=1          -- 1 to drop any field > max_bytes, 0 to only drop drop_keys
--   -v drop_keys='k1,k2,k3'     -- comma-separated keys to always drop
--
\set ON_ERROR_STOP on
\set apply 0
\set max_bytes 50000
\set prune_by_size 1
\set drop_keys 'text_content_info,data_fields,data_statistics,data_domains,compression_info,file_integrity,format_version,document_pages,spreadsheet_sheets,content_type_detected,geographic_coverage,administrative_boundaries'

DROP TABLE IF EXISTS _schemingdcat_extras_cleanup;

CREATE TEMP TABLE _schemingdcat_extras_cleanup AS
WITH target AS (
  SELECT id, extras::jsonb AS j
  FROM resource
  WHERE extras IS NOT NULL AND btrim(extras) <> ''
),
filtered AS (
  SELECT
    id,
    j,
    COALESCE(
      (
        SELECT jsonb_object_agg(key, value)
        FROM jsonb_each(j)
        WHERE NOT (
          key = ANY(string_to_array(replace(:'drop_keys', ' ', ''), ','))
        )
        AND (
          :prune_by_size::int = 0
          OR :max_bytes::int <= 0
          OR octet_length(value::text) <= :max_bytes::int
        )
      ),
      '{}'::jsonb
    ) AS new_j
  FROM target
)
SELECT
  id,
  j,
  new_j,
  octet_length(j::text) AS old_bytes,
  octet_length(new_j::text) AS new_bytes
FROM filtered
WHERE new_j IS DISTINCT FROM j;

SELECT
  COUNT(*) AS resources_to_update,
  SUM(old_bytes) AS total_old_bytes,
  SUM(new_bytes) AS total_new_bytes
FROM _schemingdcat_extras_cleanup;

SELECT id, old_bytes, new_bytes
FROM _schemingdcat_extras_cleanup
ORDER BY old_bytes DESC
LIMIT 20;

DO $$
DECLARE
  v_count integer := 0;
BEGIN
  IF :apply::int = 1 THEN
    UPDATE resource r
    SET extras = c.new_j::text
    FROM _schemingdcat_extras_cleanup c
    WHERE r.id = c.id;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RAISE NOTICE 'Updated % resources', v_count;
  ELSE
    RAISE NOTICE 'Dry run only - no updates applied';
  END IF;
END $$;

DROP TABLE IF EXISTS _schemingdcat_extras_cleanup;
