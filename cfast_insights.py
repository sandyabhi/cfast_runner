# ============================================================
# cfast_insights.py
# ============================================================
#
# Reads CFAST output data and generates structured insights.
#
# This file does NOT use an LLM.
#
# Its purpose is to convert raw CFAST output into:
#
# - Basic statistics
# - Minimum / maximum values
# - Time of important events
# - Increasing / decreasing trends
# - Detected temperature information
# - Detected oxygen information
# - Detected gas information
# - Detected hazards
#
# The resulting JSON can then be sent to:
#
#   Analyst A
#   Analyst B
#   Judge LLM
#
# ============================================================


import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

class Config:

    # Number of rows included when showing sample data
    SAMPLE_ROWS = 5

    # Keywords used to identify possible CFAST variables.
    #
    # We can update these after seeing real CFAST output.

    TIME_KEYWORDS = [
        "time",
        "seconds",
        "sec"
    ]

    TEMPERATURE_KEYWORDS = [
        "temp",
        "temperature"
    ]

    OXYGEN_KEYWORDS = [
        "oxygen",
        "o2"
    ]

    CO_KEYWORDS = [
        "carbon monoxide",
        "carbon_monoxide",
        "co"
    ]

    CO2_KEYWORDS = [
        "carbon dioxide",
        "carbon_dioxide",
        "co2"
    ]

    SMOKE_KEYWORDS = [
        "smoke",
        "layer height",
        "interface"
    ]

    PRESSURE_KEYWORDS = [
        "pressure",
        "press"
    ]


# ============================================================
# HELPERS
# ============================================================

def normalize_name(name: str) -> str:
    """
    Normalize a column name for comparison.
    """

    return (
        str(name)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


def find_columns(
    columns: List[str],
    keywords: List[str]
) -> List[str]:
    """
    Find columns containing any of the specified keywords.
    """

    matches = []

    for column in columns:

        normalized = normalize_name(column)

        for keyword in keywords:

            keyword_normalized = normalize_name(keyword)

            if keyword_normalized in normalized:

                matches.append(column)

                break

    return matches


def find_time_column(
    df: pd.DataFrame
) -> Optional[str]:
    """
    Attempt to find the simulation time column.
    """

    matches = find_columns(
        list(df.columns),
        Config.TIME_KEYWORDS
    )

    if matches:

        return matches[0]

    return None


def safe_number(value: Any) -> Optional[float]:
    """
    Convert a value to float safely.
    """

    try:

        if pd.isna(value):

            return None

        return float(value)

    except Exception:

        return None


# ============================================================
# COLUMN ANALYSIS
# ============================================================

def analyze_numeric_column(
    df: pd.DataFrame,
    column: str,
    time_column: Optional[str]
) -> Dict[str, Any]:
    """
    Generate basic numerical insights for one column.
    """

    series = pd.to_numeric(
        df[column],
        errors="coerce"
    ).dropna()


    if series.empty:

        return {

            "column": column,

            "data_available": False
        }


    # --------------------------------------------------------
    # Basic statistics
    # --------------------------------------------------------

    minimum = float(series.min())

    maximum = float(series.max())

    mean = float(series.mean())

    first_value = float(series.iloc[0])

    last_value = float(series.iloc[-1])


    # --------------------------------------------------------
    # Determine trend
    # --------------------------------------------------------

    change = last_value - first_value


    if change > 0:

        trend = "increasing"

    elif change < 0:

        trend = "decreasing"

    else:

        trend = "stable"


    # --------------------------------------------------------
    # Find time of maximum/minimum
    # --------------------------------------------------------

    max_time = None
    min_time = None


    if time_column and time_column in df.columns:

        numeric_time = pd.to_numeric(
            df[time_column],
            errors="coerce"
        )


        max_index = series.idxmax()
        min_index = series.idxmin()


        if max_index in numeric_time.index:

            max_time = safe_number(
                numeric_time.loc[max_index]
            )


        if min_index in numeric_time.index:

            min_time = safe_number(
                numeric_time.loc[min_index]
            )


    return {

        "column": column,

        "data_available": True,

        "count": int(series.count()),

        "minimum": minimum,

        "minimum_time": min_time,

        "maximum": maximum,

        "maximum_time": max_time,

        "mean": mean,

        "initial_value": first_value,

        "final_value": last_value,

        "change": float(change),

        "trend": trend
    }


# ============================================================
# CATEGORY ANALYSIS
# ============================================================

def analyze_category(
    df: pd.DataFrame,
    category_name: str,
    keywords: List[str],
    time_column: Optional[str]
) -> Dict[str, Any]:
    """
    Analyze all columns matching a category.
    """

    matching_columns = find_columns(

        list(df.columns),

        keywords

    )


    results = []


    for column in matching_columns:

        result = analyze_numeric_column(

            df,

            column,

            time_column

        )

        results.append(result)


    return {

        "category": category_name,

        "matching_columns": matching_columns,

        "measurements": results
    }


# ============================================================
# GENERATE TEMPERATURE INSIGHTS
# ============================================================

def generate_temperature_insights(
    temperature_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Create objective insights from temperature data.
    """

    insights = []


    for measurement in temperature_data["measurements"]:

        if not measurement.get("data_available"):

            continue


        if measurement["trend"] == "increasing":

            insights.append({

                "type": "temperature_trend",

                "column": measurement["column"],

                "insight":
                    "Temperature increased during the simulation.",

                "initial_value":
                    measurement["initial_value"],

                "final_value":
                    measurement["final_value"],

                "maximum":
                    measurement["maximum"],

                "maximum_time":
                    measurement["maximum_time"]

            })


        elif measurement["trend"] == "decreasing":

            insights.append({

                "type": "temperature_trend",

                "column": measurement["column"],

                "insight":
                    "Temperature decreased during the simulation.",

                "initial_value":
                    measurement["initial_value"],

                "final_value":
                    measurement["final_value"]

            })


    return insights


# ============================================================
# GENERATE OXYGEN INSIGHTS
# ============================================================

def generate_oxygen_insights(
    oxygen_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate objective insights from oxygen data.
    """

    insights = []


    for measurement in oxygen_data["measurements"]:

        if not measurement.get("data_available"):

            continue


        if measurement["trend"] == "decreasing":

            insights.append({

                "type": "oxygen_decrease",

                "column": measurement["column"],

                "insight":
                    "Oxygen concentration decreased during "
                    "the simulation.",

                "initial_value":
                    measurement["initial_value"],

                "final_value":
                    measurement["final_value"],

                "minimum":
                    measurement["minimum"],

                "minimum_time":
                    measurement["minimum_time"]

            })


    return insights


# ============================================================
# GENERATE GAS INSIGHTS
# ============================================================

def generate_gas_insights(
    gas_data: Dict[str, Any],
    gas_name: str
) -> List[Dict[str, Any]]:
    """
    Generate insights for combustion gases.
    """

    insights = []


    for measurement in gas_data["measurements"]:

        if not measurement.get("data_available"):

            continue


        insights.append({

            "type": f"{gas_name}_analysis",

            "gas": gas_name,

            "column": measurement["column"],

            "initial_value":
                measurement["initial_value"],

            "final_value":
                measurement["final_value"],

            "maximum":
                measurement["maximum"],

            "maximum_time":
                measurement["maximum_time"],

            "trend":
                measurement["trend"]

        })


    return insights


# ============================================================
# GENERATE DATA QUALITY INSIGHTS
# ============================================================

def analyze_data_quality(
    df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Identify missing values and basic data quality problems.
    """

    missing_values = {}


    for column in df.columns:

        missing = int(df[column].isna().sum())


        if missing > 0:

            missing_values[column] = missing


    return {

        "total_rows": int(len(df)),

        "total_columns": int(len(df.columns)),

        "missing_values": missing_values,

        "columns": list(df.columns)
    }


# ============================================================
# GENERATE RAW DATA SUMMARY
# ============================================================

def create_data_summary(
    df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Create a compact summary of the raw data.

    This is useful for sending to the LLMs without sending
    an unnecessarily large CSV file.
    """

    numeric_columns = []


    for column in df.columns:

        if pd.api.types.is_numeric_dtype(df[column]):

            numeric_columns.append(column)


    return {

        "shape": {

            "rows": int(df.shape[0]),

            "columns": int(df.shape[1])

        },

        "column_names": list(df.columns),

        "numeric_columns": numeric_columns,

        "sample_rows":

            df.head(
                Config.SAMPLE_ROWS
            ).to_dict(

                orient="records"

            )
    }


# ============================================================
# MAIN CFAST INSIGHT ENGINE
# ============================================================

def generate_cfast_insights(
    file_path: str
) -> Dict[str, Any]:
    """
    Main function.

    Reads a CSV file and generates structured insights.
    """

    path = Path(file_path)


    if not path.exists():

        raise FileNotFoundError(

            f"File not found: {file_path}"

        )


    print(f"📂 Reading CFAST data: {path.name}")


    # --------------------------------------------------------
    # Load CSV
    # --------------------------------------------------------

    df = pd.read_csv(path)


    print(

        f"📊 Loaded "

        f"{len(df)} rows × "

        f"{len(df.columns)} columns"

    )


    # --------------------------------------------------------
    # Find time column
    # --------------------------------------------------------

    time_column = find_time_column(df)


    print(

        f"⏱️ Time column: "

        f"{time_column or 'Not detected'}"

    )


    # --------------------------------------------------------
    # Analyze categories
    # --------------------------------------------------------

    temperature_data = analyze_category(

        df,

        "temperature",

        Config.TEMPERATURE_KEYWORDS,

        time_column

    )


    oxygen_data = analyze_category(

        df,

        "oxygen",

        Config.OXYGEN_KEYWORDS,

        time_column

    )


    co_data = analyze_category(

        df,

        "carbon_monoxide",

        Config.CO_KEYWORDS,

        time_column

    )


    co2_data = analyze_category(

        df,

        "carbon_dioxide",

        Config.CO2_KEYWORDS,

        time_column

    )


    smoke_data = analyze_category(

        df,

        "smoke",

        Config.SMOKE_KEYWORDS,

        time_column

    )


    pressure_data = analyze_category(

        df,

        "pressure",

        Config.PRESSURE_KEYWORDS,

        time_column

    )


    # --------------------------------------------------------
    # Generate objective insights
    # --------------------------------------------------------

    insights = []


    insights.extend(

        generate_temperature_insights(

            temperature_data

        )

    )


    insights.extend(

        generate_oxygen_insights(

            oxygen_data

        )

    )


    insights.extend(

        generate_gas_insights(

            co_data,

            "carbon_monoxide"

        )

    )


    insights.extend(

        generate_gas_insights(

            co2_data,

            "carbon_dioxide"

        )

    )


    # --------------------------------------------------------
    # Build final output
    # --------------------------------------------------------

    result = {

        "source_file": path.name,

        "data_summary":

            create_data_summary(df),


        "data_quality":

            analyze_data_quality(df),


        "detected_time_column":

            time_column,


        "categories": {

            "temperature":

                temperature_data,


            "oxygen":

                oxygen_data,


            "carbon_monoxide":

                co_data,


            "carbon_dioxide":

                co2_data,


            "smoke":

                smoke_data,


            "pressure":

                pressure_data

        },


        "objective_insights":

            insights

    }


    return result


# ============================================================
# SAVE INSIGHTS
# ============================================================

def save_insights(
    insights: Dict[str, Any],
    output_file: str = "cfast_insights.json"
):
    """
    Save generated insights as JSON.
    """

    with open(

        output_file,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            insights,

            file,

            indent=2,

            ensure_ascii=False

        )


    print(

        f"💾 Insights saved to: "

        f"{output_file}"

    )


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # CHANGE THIS TO YOUR CFAST CSV FILE
    # --------------------------------------------------------

    INPUT_FILE = "cfast_output.csv"


    try:

        insights = generate_cfast_insights(

            INPUT_FILE

        )


        save_insights(insights)


        print("\n🔥 CFAST INSIGHTS GENERATED\n")


        print(

            json.dumps(

                insights,

                indent=2

            )

        )


    except FileNotFoundError as error:

        print(f"\n❌ {error}")


        print(

            "\nChange INPUT_FILE to the path of "

            "your CFAST output CSV."

        )