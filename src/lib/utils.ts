export function formatSafeDate(dateVal: any, lang: string): string {
    if (!dateVal) return "—";
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleString(lang === "en" ? "en-US" : "vi-VN");
}

export function formatSafeTime(dateVal: any, lang: string): string {
    if (!dateVal) return "—";
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleTimeString(lang === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" });
}
