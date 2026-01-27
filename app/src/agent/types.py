"""
src/agent/roles.py

Configures agent's prompts and roles for different stages of operation.

"""

from enum import Enum
from typing import Dict

ETL_PIPELINE_STAGES = [
    "data-discovery",
    "data-modelling",
    "data-transformation",
]

DATA_TRANS_ACTIONS: Dict[str, Dict[str, str]] = {
    "missing-values-handling": {
        "drop_rows": "Remove rows containing missing values in selected columns.",
        "mean_imputation": "Replace missing numeric values with the mean of observed values.",
        "median_imputation": "Replace missing numeric values with the median to reduce outlier sensitivity.",
        "mode_imputation": "Replace missing values with the most frequent observed value.",
        "constant_imputation": "Replace missing values with a fixed constant such as zero or a sentinel value.",
        "forward_fill": "Propagate the last valid observation forward to fill missing values.",
        "backward_fill": "Propagate the next valid observation backward to fill missing values.",
        "interpolation_linear": "Estimate missing values using linear interpolation between neighboring points.",
        "interpolation_time": "Interpolate missing values using time-based indexing for temporal data.",
        "knn_imputation": "Impute missing values using k-nearest neighbors based on feature similarity.",
        "iterative_imputation": "Iteratively model each feature with missing values as a function of other features.",
        "regression_imputation": "Predict missing values using a regression model trained on observed data.",
    },
    "outlier-handling": {
        "iqr_clipping": "Cap values outside the interquartile range using lower and upper bounds.",
        "zscore_clipping": "Cap or flag values exceeding a specified z-score threshold.",
        "winsorization": "Replace extreme values with percentile-based boundary values.",
        "isolation_forest_detection": "Identify outliers using an ensemble-based isolation forest model.",
        "local_outlier_factor": "Detect anomalous points based on local density deviations.",
        "dbscan_outlier_removal": "Identify and remove noise points using density-based clustering.",
        "robust_scaling": "Reduce outlier influence by scaling features using robust statistics.",
    },
    "encoding": {
        "one_hot_encoding": "Encode categorical variables as binary indicator columns.",
        "ordinal_encoding": "Encode ordered categorical variables using integer rankings.",
        "label_encoding": "Encode categorical values as integer labels without preserving order.",
        "target_encoding": "Encode categories using aggregated target statistics.",
        "frequency_encoding": "Encode categories based on observed frequency.",
        "binary_encoding": "Encode categories using binary representations to reduce dimensionality.",
        "hashing_trick": "Map categorical values to a fixed-dimensional space using a hash function.",
    },
    "scaling-normalization": {
        "min_max_scaling": "Scale features to a fixed range, typically between zero and one.",
        "standard_scaling": "Standardize features to zero mean and unit variance.",
        "robust_scaling": "Scale features using median and interquartile range for robustness to outliers.",
        "max_abs_scaling": "Scale features by their maximum absolute value.",
        "log_transform": "Apply a logarithmic transformation to reduce skewness in distributions.",
        "power_transform_yeo_johnson": "Apply a power transformation to stabilize variance and normalize distributions.",
        "quantile_transform": "Transform features to follow a uniform or normal distribution.",
    },
    "binning-discretization": {
        "equal_width_binning": "Discretize continuous values into bins of equal width.",
        "equal_frequency_binning": "Discretize values so each bin contains approximately equal observations.",
        "quantile_binning": "Create bins based on specified quantiles of the data distribution.",
        "kmeans_binning": "Use k-means clustering to define bin boundaries.",
        "decision_tree_binning": "Learn bin thresholds using decision tree splits.",
        "custom_threshold_binning": "Discretize values using predefined domain-specific thresholds.",
    },
    "feature-construction": {
        "polynomial_features": "Generate polynomial combinations of numeric features.",
        "interaction_terms": "Create features representing interactions between existing variables.",
        "ratio_features": "Derive new features as ratios between numeric variables.",
        "aggregation_features": "Compute aggregated statistics over grouped dimensions.",
        "lag_features": "Create lagged versions of variables for temporal modeling.",
        "rolling_window_features": "Compute rolling statistics over a defined window size.",
        "date_part_features": "Extract calendar-based features such as weekday, month, or quarter.",
    },
    "dimensionality-reduction": {
        "pca": "Reduce dimensionality using principal component analysis.",
        "incremental_pca": "Apply PCA in batches for large or streaming datasets.",
        "kernel_pca": "Perform non-linear dimensionality reduction using kernel methods.",
        "truncated_svd": "Reduce dimensionality using truncated singular value decomposition.",
        "autoencoder_projection": "Learn a low-dimensional representation using neural autoencoders.",
        "variance_threshold": "Remove features with variance below a specified threshold.",
        "correlation_filtering": "Drop features that are highly correlated with others.",
    },
}


# Session Base Dataset
class GenerateCodeDtypeConfig(Enum):
    """ Configuration for generating code based on data types. """
    pandasDtype = {
        "bool":      "OBO",  # boolean
        "datetime":  "ODT",  # datetime64[ns], datetime64[ns, tz]
        "timedelta": "ODT",  # treat as time-like; keep same family if desired
        "numeric":   "NCO",  # all numeric (int/float) without value-based splitting
        "category":  "CBI",  # pandas 'category' dtype (categorical)
        "string":    "OTX",  # pandas StringDtype
        "object":    "OTX",  # object (often text/categorical; we treat as text to avoid heuristics)
        "None":     "OUK"   # unknown / other dtypes
    }
    categoryCode = {
        "numerical": "N",
        "categorical": "C",
        "others": "O"
    }
    subCode = {
        "continuous": "NC",
        "discrete": "ND",
        "nominal": "NN",
        "ordinal": "NO",
        "binary-label": "CB",
        "multi-label": "CM",
        "datetime": "OD",
        "geospatial": "OG",
        "text": "OT",
        "boolean": "OB",
        "identifier": "OI",
    }

class DataTypeCategories(Enum):
    """ Data Type Categories for Tabular Dataset Profiling. """
    parent = ["numerical", "categorical", "others"]
    numerical = [ "continuous", "discrete", "nominal", "ordinal"]
    categorical = ["binary-label", "multi-label"]
    others = ["datetime", "geospatial", "text", "boolean", "identifier"]
    codeDtype = GenerateCodeDtypeConfig

class AgentTabularFields(Enum):
    """ Tabular Tables Configs used pass between agent orchestrations. """
    SUMMARY = ["data_field_name", "data_type", "null_counts", "unique_counts", "mean", "min", "max"]
    FACT_TABLE = ["data_field_name", "data_type", "description", "data_type_category", "data_type_subcategory"]
    VALUE_TYPE_TABLE = ["data_field_name", "nested"]


class SkeletonAgentInputs(Enum):
    PLANNER = """Data processing stage instruction: {objective}\nCurrent Dataset Schema Model:\n{dataset_schema}\n"""
    EXECUTOR = """TODO Task: {current_step}\nCurrent Dataset Schema Model:\n{dataset_schema}\n"""
    EVALUATOR = """Results from executed task: {results}\nCurrent Dataset Schema Model:\n{dataset_schema}\n"""

class SkeletonAgentResponseTemplate(Enum):
    PLANNER = "{{'steps': [str, str, str]}}"
    EXECUTOR = "{{'code': str}}"
    EVALUATOR = "{{'success': bool, 'feedback': str | null, 'reason': str | null }}"

class SkeletonAgentRole(Enum):
    PLANNER = "Given the dataset schema model, create a 3 step plan for the following data processing stage. Provide your response in the following JSON format {} where 'steps' is a list of 3 sequential steps to accomplish the task.".format(SkeletonAgentResponseTemplate.PLANNER.value)
    EXECUTOR = "Given the TODO data engineering task amd the data model schema, provide python code that performs data wrangling operations to manipulate the pandas dataframes. Provide your response in JSON format {} with key `code` containing the python code script with dataframe parameters.".format(SkeletonAgentResponseTemplate.EXECUTOR.value)
    EVALUATOR = "Evaluate the results from executed task and provide feedback onto whether the task was successful or not. Provide your response in the following JSON format {} where 'success' indicates if the task was completed successfully, 'feedback' provides suggestions for improvement if any and otherwise defaults to null, and 'reason' provides reason for failure if any otherwise leave it as null.".format(SkeletonAgentResponseTemplate.EVALUATOR.value)



PROFILE_TABULAR_FIELD_META = """
data_field_name: Name of the data column
description: Brief description of the data column.
data_type: Specific data type of the column (e.g., integer, string, date).
data_type_category: General category of the data type (e.g., numeric, categorical, temporal).
data_type_subcategory: More specific subcategory if applicable (e.g., continuous, discrete for numeric types).
"""
MODELLER_TABULAR_FIELD_META = """
data_field_name: Name of the data column
nested: Boolean indicating if the field is nested (e.g., JSON, array).
to_do: Suggested data modelling operation to improve data quality or usability.
"""

TABULAR_FIELD_META = PROFILE_TABULAR_FIELD_META + MODELLER_TABULAR_FIELD_META


class DataAgentResponseTemplate(Enum):
    profiler = "{{'outputs': [{{'data_field_name': str, 'description': str, 'data_type': str, 'description': str, 'data_type_category': str, 'data_type_subcategory': str}}]}}"
    modeller = "{{'outputs': [{{'data_field_name': str, 'nested': bool, 'to_do': str | null}}]}}"
    MissingValuesHandling = "{{'outputs': [{{'data_field_name': str, 'missing_reason': float, 'missing_pattern': str, 'handling_action': str}}]}}"
    Deduplication = f"{{'outputs': [{{'data_field_name': str, 'candidate_key': bool, 'fuzzy_matching_rules': str | null}}]}}"
    OutlierDetection = "{{'outputs': [{{'data_field_name': str, 'outlier_percentage': float, 'detection_method': str, 'handling_action': str}}]}}"

class DataAgentInputsTemplate(Enum):
    profiler = """Dataset Profile Summary:\n{data_profile}\nSample Data Preview:\n{data_sample}"""
    modeller = """Dataset Profile Summary:\n{data_profile}"""
    MissingValuesHandling = """Dataset Profile Summary:\n{data_profile}\nObjective: {objective}\nCurrent Data Issues: {data_issues}"""
    Deduplication = """Dataset Profile Summary:\n{data_profile}\nObjective: {objective}\nCurrent Data Issues: {data_issues}"""
    OutlierDetection = """Dataset Profile Summary:\n{data_profile}\nObjective: {objective}\nCurrent Data Issues: {data_issues}"""

class DataAgentRoleConfig(Enum):
    profiler = "Given the dataset's objective and data model summary, Return the description of the data column fields and their data types. Provide your response in the following JSON format {} where 'outputs' is a list of objects containing: {}".format(DataAgentResponseTemplate.profiler.value, TABULAR_FIELD_META.strip())

    modeller = "Given the dataset's objective, data model summary, and current data issues, suggest data restructuring operations to improve data quality and usability. Provide your response in the following JSON format {} where 'suggested_operations' is a list of 3 recommended data restructuring operations.".format(DataAgentResponseTemplate.modeller.value)
    MissingValuesHandling = (
        "Given the dataset field summary report and the sample values for the respective data fields, for datasets where there exists missing values, analyze the patterns of missingness and recommend appropriate strategies. Return your response in the following JSON format: {}."
    ).format(DataAgentResponseTemplate.MissingValuesHandling.value)
    Deduplication = (
        "Detect and remove duplicate records from the dataset, keeping the most complete or recent version "
        "of each unique entry. Given the dataset's objective, schema model, and current data issues, propose "
        "a deduplication design including candidate keys, fuzzy matching rules (when needed), survivorship "
        "logic, and an audit trail. Provide your response in the following JSON format {}."
    ).format(DataAgentResponseTemplate.Deduplication.value)

    OutlierDetection = (
        "Identify outliers and anomalous values using statistical methods, then flag or handle them "
        "according to whether they represent errors or valid extreme cases. Given the dataset's objective, "
        "schema model, and current data issues, propose column-specific detection methods and handling "
        "actions. Provide your response in the following JSON format {}. Use robust "
        "statistics (IQR/MAD) where appropriate, and consider temporal/group-aware detection when relevant."
    ).format(DataAgentResponseTemplate.OutlierDetection.value)

