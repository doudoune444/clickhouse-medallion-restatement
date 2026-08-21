-- Projection of one `meta_ads` extraction onto Bronze: same procedure, other schema.
INSERT INTO bronze.{staging_table:Identifier}
SELECT
    'meta_ads'                   AS _source,
    concat('s3://', _path)       AS _source_file,
    toDate({extracted_at:String}) AS _extracted_at,
    now()                        AS _ingested_at,
    account_id,
    campaign_id,
    date_start,
    spend,
    clicks,
    impressions,
    conversions,
    revenue_eur
FROM s3({extraction_url:String}, 'Parquet');
