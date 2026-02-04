SELECT COUNT(*) AS raw_cnt FROM used_car_raw;
SELECT * FROM used_car_raw LIMIT 3;

CREATE TABLE IF NOT EXISTS dim_brand (
  brand_id INT AUTO_INCREMENT PRIMARY KEY,
  brand_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_car_listing (
  listing_id BIGINT AUTO_INCREMENT PRIMARY KEY,

  brand_id INT NOT NULL,
  model_name_raw VARCHAR(255) NOT NULL,
  model_key VARCHAR(120) NOT NULL,

  year_int INT NULL,
  mileage_km INT NULL,
  price_manwon INT NULL,

  fuel_type VARCHAR(50) NULL,
  region VARCHAR(100) NULL,

  url VARCHAR(500) NULL,

  raw_id BIGINT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_brand FOREIGN KEY (brand_id) REFERENCES dim_brand(brand_id),

  INDEX idx_model_key (model_key),
  INDEX idx_year_mileage (year_int, mileage_km),
  INDEX idx_price (price_manwon)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

show tables;

INSERT IGNORE INTO dim_brand(brand_name)
SELECT DISTINCT TRIM(brand)
FROM used_car_raw
WHERE brand IS NOT NULL AND TRIM(brand) <> '';

select * from dim_brand;

CREATE TABLE fact_car_listing (
  listing_id BIGINT AUTO_INCREMENT PRIMARY KEY,

  brand_id INT NOT NULL,
  model_name_raw VARCHAR(255) NOT NULL,

  year_int INT NULL,
  mileage_km INT NULL,
  price_manwon INT NULL,

  fuel_type VARCHAR(50) NULL,
  region VARCHAR(100) NULL,
  url VARCHAR(500) NULL,

  raw_id BIGINT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_brand FOREIGN KEY (brand_id) REFERENCES dim_brand(brand_id),

  INDEX idx_brand (brand_id),
  INDEX idx_year_mileage (year_int, mileage_km),
  INDEX idx_price (price_manwon)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='clean+정규화 완료 매물 fact 테이블 (분석/streamlit용)';

show tables;
desc fact_car_listing;

INSERT INTO fact_car_listing (
  brand_id, model_name_raw,
  year_int, mileage_km, price_manwon,
  fuel_type, region, url, raw_id
)
SELECT
  b.brand_id,
  r.model_name AS model_name_raw,

  -- year_int: "18/03" -> 2018 (숫자 없으면 NULL)
  CASE
    WHEN r.year IS NULL OR TRIM(r.year) = '' THEN NULL
    ELSE
      CASE
        WHEN CAST(NULLIF(REGEXP_REPLACE(SUBSTRING_INDEX(TRIM(r.year), '/', 1), '[^0-9]', ''), '') AS UNSIGNED) <= 30
          THEN 2000 + CAST(NULLIF(REGEXP_REPLACE(SUBSTRING_INDEX(TRIM(r.year), '/', 1), '[^0-9]', ''), '') AS UNSIGNED)
        WHEN CAST(NULLIF(REGEXP_REPLACE(SUBSTRING_INDEX(TRIM(r.year), '/', 1), '[^0-9]', ''), '') AS UNSIGNED) < 100
          THEN 1900 + CAST(NULLIF(REGEXP_REPLACE(SUBSTRING_INDEX(TRIM(r.year), '/', 1), '[^0-9]', ''), '') AS UNSIGNED)
        ELSE NULL
      END
  END AS year_int,

  -- mileage_km: "12만km" -> 120000, "120,000km" -> 120000 (숫자 없으면 NULL)
  CASE
    WHEN r.mileage IS NULL OR TRIM(r.mileage) = '' THEN NULL
    WHEN NULLIF(REGEXP_REPLACE(TRIM(r.mileage), '[^0-9]', ''), '') IS NULL THEN NULL
    WHEN TRIM(r.mileage) LIKE '%만%' THEN
      CAST(NULLIF(REGEXP_REPLACE(TRIM(r.mileage), '[^0-9]', ''), '') AS UNSIGNED) * 10000
    ELSE
      CAST(NULLIF(REGEXP_REPLACE(TRIM(r.mileage), '[^0-9]', ''), '') AS UNSIGNED)
  END AS mileage_km,

  -- price_manwon: "1,350만원" -> 1350, "계약" -> NULL
  CASE
    WHEN r.price IS NULL OR TRIM(r.price) = '' THEN NULL
    WHEN NULLIF(REGEXP_REPLACE(TRIM(r.price), '[^0-9]', ''), '') IS NULL THEN NULL
    ELSE CAST(REGEXP_REPLACE(TRIM(r.price), '[^0-9]', '') AS UNSIGNED)
  END AS price_manwon,

  -- ⚠️ 아래 3개는 raw 컬럼명에 맞춰야 함 (fuel_type/url 컬럼명이 다르면 수정)
  r.fuel_type,
  r.region,
  r.url,

  r.id AS raw_id

FROM used_car_raw r
JOIN dim_brand b ON b.brand_name = TRIM(r.brand);

select count(*) from fact_car_listing;