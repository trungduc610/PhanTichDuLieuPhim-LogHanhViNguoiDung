"""Official Spark schemas for Movie metadata and User Behavior Logs.

Designed for Week 1 validation and reusable for Week 2 processing.
"""
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    IntegerType,
    BooleanType,
)

# 1. Movie Dataset Schema
# Source: data/processed/movies.csv (Metadata phim)
MOVIE_SCHEMA = StructType([
    StructField("movieId", LongType(), nullable=False),
    StructField("title", StringType(), nullable=False),
    StructField("genres", StringType(), nullable=False),
    StructField("releaseYear", IntegerType(), nullable=True),
])

# 2. User Behavior Log Schema
# Source: Apache Flume Output JSONL (Log hành vi người dùng)
USER_LOG_SCHEMA = StructType([
    StructField("eventId", StringType(), nullable=False),
    StructField("userId", StringType(), nullable=False),
    StructField("sessionId", StringType(), nullable=False),
    StructField("movieId", LongType(), nullable=False),
    StructField("action", StringType(), nullable=False),
    StructField("timestamp", StringType(), nullable=False),
    StructField("watchDuration", LongType(), nullable=False),
    StructField("sequenceNumber", LongType(), nullable=False),
    StructField("runId", StringType(), nullable=False),
    StructField("isSynthetic", BooleanType(), nullable=False),
    StructField("simulatedMovieDuration", LongType(), nullable=False),
    StructField("durationSource", StringType(), nullable=False),
])
