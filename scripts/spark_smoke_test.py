"""Spark smoke test for Week 1 environment and schema verification.

Scope:
- Validates SparkSession creation.
- Prints Spark, Python, and Java environment info.
- Reads movies.csv with explicit MOVIE_SCHEMA.
- Reads Flume JSONL output with explicit USER_LOG_SCHEMA.
- Verifies movieId join compatibility without running any aggregations or analysis.
"""
import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path so src.schemas can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.schemas import MOVIE_SCHEMA, USER_LOG_SCHEMA

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main():
    parser = argparse.ArgumentParser(description="Spark Week 1 Smoke Test")
    parser.add_argument(
        "--movies-path",
        default=str(ROOT / "data" / "processed" / "movies.csv"),
        help="Path to processed movies.csv",
    )
    parser.add_argument(
        "--logs-path",
        default=str(ROOT / "data" / "runs" / "run-f63c810e9d8d" / "output" / "*.jsonl"),
        help="Glob pattern to Flume output jsonl files",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("STARTING SPARK SMOKE TEST (WEEK 1 VALIDATION)")
    print("=" * 60)

    # 1. Initialize SparkSession
    spark = (
        SparkSession.builder
        .appName("MovieLog-Week1-SmokeTest")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", "1g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    # 2. Print environment details
    print(f"[INFO] Spark Version: {spark.version}")
    print(f"[INFO] Python Executable: {sys.executable}")
    print(f"[INFO] Python Version: {sys.version.split()[0]}")
    java_version = spark._jvm.System.getProperty("java.version")
    print(f"[INFO] Java Version in JVM: {java_version}")

    # 3. Simple DataFrame verification
    print("\n--- 1. Basic DataFrame Test ---")
    df_range = spark.range(5)
    df_range.show()
    print("[PASS] spark.range(5) executed successfully.")

    # 4. Read Movie Dataset
    print("\n--- 2. Reading Movie Dataset ---")
    print(f"[INFO] Movies path: {args.movies_path}")
    movies_df = (
        spark.read
        .option("header", "true")
        .option("encoding", "UTF-8")
        .schema(MOVIE_SCHEMA)
        .csv(args.movies_path)
    )
    print("\nMovie Schema:")
    movies_df.printSchema()

    movie_count = movies_df.count()
    print(f"[INFO] Total movie records: {movie_count}")
    assert movie_count == 9742, f"Expected 9742 movies, got {movie_count}"
    print("[PASS] Movie count verified (9,742 records).")

    print("\nSample Movies:")
    movies_df.show(5, truncate=False)

    # 5. Read User Behavior Log from Flume Output
    print("\n--- 3. Reading Flume JSONL Output ---")
    print(f"[INFO] Logs path pattern: {args.logs_path}")
    logs_df = (
        spark.read
        .option("mode", "FAILFAST")
        .schema(USER_LOG_SCHEMA)
        .json(args.logs_path)
    )
    print("\nUser Log Schema:")
    logs_df.printSchema()

    log_count = logs_df.count()
    print(f"[INFO] Total log records from Flume output: {log_count}")
    assert log_count > 0, "No log records found in Flume output path!"
    print(f"[PASS] Successfully read {log_count:,} records from Flume output.")

    print("\nSample User Logs:")
    logs_df.select("eventId", "userId", "movieId", "action", "watchDuration", "timestamp").show(5, truncate=False)

    # 6. Verify movieId presence and Join Key Compatibility
    print("\n--- 4. Join Key Compatibility Check (movieId) ---")
    sample_log_movie_id = logs_df.select("movieId").first()[0]
    matched_movie = movies_df.filter(F.col("movieId") == sample_log_movie_id).count()
    print(f"[INFO] Sample log movieId={sample_log_movie_id} matched in movies.csv: {matched_movie > 0}")
    assert matched_movie > 0, f"movieId {sample_log_movie_id} not found in movies!"

    # Minimal inner join check (limit 5 sample only, NO aggregation / NO analysis)
    print("\nValidating minimal join execution (Sample 5 rows):")
    sample_joined = (
        logs_df.select("eventId", "userId", "movieId", "action", "watchDuration")
        .limit(5)
        .join(movies_df.select("movieId", "title", "genres"), on="movieId", how="inner")
    )
    sample_joined.show(truncate=False)
    assert sample_joined.count() > 0, "Join between movies and logs yielded 0 rows!"
    print("[PASS] Join on movieId validated successfully.")

    print("\n" + "=" * 60)
    print("ALL WEEK 1 SPARK SMOKE TESTS PASSED SUCCESSFULLY!")
    print("Flume output is ready for Spark/PySpark Week 2 processing.")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    main()
