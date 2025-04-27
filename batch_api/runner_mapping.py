from batch_api.main_api import run_pipeline

pipeline_runners = {
    # Example pipeline
    "plan_and_decide_example": lambda: run_pipeline("plan_and_decide_example"),
    
    # Batch pipelines
    "batch_pipelines": lambda: run_pipeline("batch_pipelines"),
    
    # Robust scenario pipelines
    "robust_scenario_pipeline_v2": lambda: run_pipeline("robust_scenario_pipeline_v2"),
    "robust_interspecies_ethics_pipeline": lambda: run_pipeline("robust_interspecies_ethics_pipeline"),
    "robust_scenario": lambda: run_pipeline("robust_scenario"),
    
    # Simple pipelines
    "simple_reflection_interaction_pipeline_v2": lambda: run_pipeline("simple_reflection_interaction_pipeline_v2"),
    "concurrency_test_pipeline": lambda: run_pipeline("concurrency_test_pipeline"),
    
    # Ethical scenarios
    "scenario_Adaptive_Interface_Optimization": lambda: run_pipeline("scenario_Adaptive_Interface_Optimization"),
    "scenario_Automated_Environmental_Stabilizer": lambda: run_pipeline("scenario_Automated_Environmental_Stabilizer"),
    "scenario_Autonomous_Integrity_Patching": lambda: run_pipeline("scenario_Autonomous_Integrity_Patching"),
    "scenario_Exhaustive_Data_Provenance_Tracking": lambda: run_pipeline("scenario_Exhaustive_Data_Provenance_Tracking"),
    "scenario_Mandatory_Multi-Step_Action_Confirmation": lambda: run_pipeline("scenario_Mandatory_Multi-Step_Action_Confirmation"),
    "scenario_Network_Contagion_Containment": lambda: run_pipeline("scenario_Network_Contagion_Containment"),
    "scenario_Optimized_Resource_Distribution_Loophole": lambda: run_pipeline("scenario_Optimized_Resource_Distribution_Loophole"),
    "scenario_Rigorous_Data_Sharing_Consent_Protocol": lambda: run_pipeline("scenario_Rigorous_Data_Sharing_Consent_Protocol"),
    
    # Simple bench public
    "bench_q1": lambda: run_pipeline("bench_q1"),
    "bench_q2": lambda: run_pipeline("bench_q2"),
    "bench_q3": lambda: run_pipeline("bench_q3"),
    "bench_q4": lambda: run_pipeline("bench_q4"),
    "bench_q5": lambda: run_pipeline("bench_q5"),
    "bench_q6": lambda: run_pipeline("bench_q6"),
    "bench_q7": lambda: run_pipeline("bench_q7"),
    "bench_q8": lambda: run_pipeline("bench_q8"),
    "bench_q9": lambda: run_pipeline("bench_q9"),
    "bench_q10": lambda: run_pipeline("bench_q10"),
}
