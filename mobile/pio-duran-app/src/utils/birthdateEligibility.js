export function birthdateEligibility(birthdate, electionDate) {
    if (!birthdate || !electionDate) return null;
    const [ey, em, ed] = electionDate.split("-").map(Number);
    const [by, bm, bd] = birthdate.split("-").map(Number);
    const age = ey - by - ((em < bm || (em === bm && ed < bd)) ? 1 : 0);
    const label = new Date(ey, em - 1, ed).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    const category = age < 15 ? "below the minimum age of 15" : age < 18 ? "SK age requirement met" : age <= 30 ? "Regular voter and SK age requirements met" : "Regular voter age requirement met";
    return { age, eligible: age >= 15, message: `Age ${age} on ${label}: ${category}.`, error: age < 15 ? `You must turn 15 on or before election day (${label}).` : "" };
}
