
schema_append = """

class EvaluationResult(BaseModel):
    eval_id: str
    metrics: dict[str, float]
    details: dict[str, Any] = Field(default_factory=dict)
    status: str
"""

repo_append = """
class EvaluationRepository:
    def __init__(self, conn):
        self.conn = conn

    def save(self, result):
        import json
        self.conn.execute(
            '''
            INSERT INTO analysis (analysis_id, generation_id, mean_delta_e, symmetry_score, seam_score, result_json_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(analysis_id) DO UPDATE SET result_json_path=excluded.result_json_path
            ''',
            (result.eval_id, "mock_gen", 0.0, result.metrics.get('symmetry_avg', 0.0), result.metrics.get('seam_continuity_avg', 0.0), json.dumps(result.metrics))
        )
        self.conn.commit()
"""

with open('src/carpet_designer/domain/schemas.py', 'a') as f:
    f.write(schema_append)

with open('src/carpet_designer/persistence/repositories.py', 'a') as f:
    f.write(repo_append)
