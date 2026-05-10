// Minimal type shim — replace with @types/papaparse when peer conflicts resolve.
declare module "papaparse" {
  export interface ParseConfig {
    header?: boolean;
    skipEmptyLines?: boolean;
    [key: string]: unknown;
  }
  export interface ParseResult<T = unknown> {
    data: T[];
    errors: unknown[];
    meta: unknown;
  }
  export function parse<T = unknown>(input: string, config?: ParseConfig<T>): ParseResult<T>;
}
