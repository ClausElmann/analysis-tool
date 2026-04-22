import re, sys
sys.path.insert(0, 'scripts/harvest')

def _extract_url(jl):
    sq = re.search(r"'([a-zA-Z][^']+)'", jl)
    if sq: return sq.group(1)
    dq = re.search(r'"([a-zA-Z][^"]+)"', jl)
    if dq: return dq.group(1)
    tl = re.search(r'`([^`]+)`', jl)
    if tl: return re.sub(r'\$\{[^}]+\}', '{param}', tl.group(1))
    ar = re.search(r'ApiRoutes[A-Za-z0-9]*\.([A-Za-z0-9_.]+)', jl)
    if ar: return '{ApiRoutes.' + ar.group(1) + '}'
    return None

tests = [
    '    return this.http.get<MySendersModel>(ApiRoutesEn.enrollmentRoutes.get.getMySendersModel).pipe(',
    '    return this.http.post(ApiRoutesEn.enrollmentRoutes.create.addEnrollments, dtos).pipe(',
    '      .delete(ApiRoutesEn.enrollmentRoutes.delete.deleteEnrollment, {',
    '    return this.http.get(ApiRoutes.someRoute)',
]
for t in tests:
    print(repr(_extract_url(t)))
