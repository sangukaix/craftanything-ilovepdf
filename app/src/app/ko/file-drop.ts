export function validateFiles(files: File[], accept: string, multiple: boolean): string | null {
  if (!files.length) return "파일을 선택하세요.";
  if (!multiple && files.length !== 1) return "파일을 하나만 선택하세요.";
  const allowed = accept.toLowerCase().split(",").map(part => part.trim()).filter(Boolean);
  const invalid = files.some(file => !allowed.some(rule =>
    rule.startsWith(".") ? file.name.toLowerCase().endsWith(rule) : file.type.toLowerCase() === rule
  ));
  return invalid ? `지원하지 않는 파일입니다. ${accept} 형식만 선택하세요.` : null;
}
