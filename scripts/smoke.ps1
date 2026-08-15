$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"
$resumeText = [string](Get-Content -Raw -LiteralPath "data\sample\sample_resume.txt")
$resume = Invoke-RestMethod -Method Post -Uri "$base/api/resumes/text" -ContentType "application/json" -Body (@{ text = $resumeText } | ConvertTo-Json)
$matches = Invoke-RestMethod -Method Post -Uri "$base/api/career-matches" -ContentType "application/json" -Body (@{ resume_id = $resume.resume_id; top_k = 5 } | ConvertTo-Json)
$target = $matches.matches[0].occupation_id
$analysis = Invoke-RestMethod -Method Post -Uri "$base/api/analyses" -ContentType "application/json" -Body (@{ resume_id = $resume.resume_id; target_occupation_id = $target; maximum_courses = 4; preferred_level = "beginner"; maximum_duration_hours = 40 } | ConvertTo-Json)
$analysis | Select-Object target_occupation, match_score, coverage_score, generation_mode, degraded_sources | Format-List
