-- Projection of one `google_ads` extraction onto Bronze: columns are copied as they
-- come, only the technical ones are added. `_path` is the S3 key the row was read from.
INSERT INTO bronze.{staging_table:Identifier}
SELECT
    'google_ads'                 AS _source,
    concat('s3://', _path)       AS _source_file,
    toDate({extracted_at:String}) AS _extracted_at,
    now()                        AS _ingested_at,
    account_id,
    campaign_id,
    product_id,
    segments_date,
    cost_micros,
    clicks,
    impressions,
    conversions,
    revenue_eur
FROM s3({extraction_url:String}, 'Parquet');
