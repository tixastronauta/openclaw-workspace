import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Briefcase, Clock, Globe, Star, StarOff, TrendingDown, TrendingUp, User, Users } from "lucide-react";

export const TOP10_ICONS: Record<string, LucideIcon> = {
  "media-entrada-mais-alta":    TrendingUp,
  "media-entrada-mais-baixa":   TrendingDown,
  "mais-homens":                User,
  "mais-mulheres":              Users,
  "media-mais-alta":            Star,
  "media-mais-baixa":           StarOff,
  "melhor-empregabilidade":     Briefcase,
  "pior-empregabilidade":       AlertTriangle,
  "mais-estrangeiros":          Globe,
  "perfil-etario-mais-elevado": Clock,
};
