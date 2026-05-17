import type { LucideIcon } from "lucide-react";
import {
  Atom, Banknote, BarChart2, BookOpen, Brain, Briefcase, Building, Building2,
  Calculator, Car, Code, Cpu, Dna, Dumbbell, FileText, Film, FlaskConical,
  Flower2, Globe, GraduationCap, Hammer, HardHat, HeartHandshake, HeartPulse,
  HelpCircle, Landmark, Leaf, Library, Map, Megaphone, Microscope, Monitor,
  Mountain, Music, Newspaper, Package, Palette, Paintbrush, PawPrint, PenTool,
  Pill, Scale, School, Scissors, Shield, ShieldCheck, Shirt, Smile, Stethoscope,
  TreePine, TrendingUp, Truck, UtensilsCrossed, Users, Wheat, Wrench, Zap,
} from "lucide-react";

export const AREA_ICONS: Record<string, LucideIcon> = {
  // Educação
  "142": GraduationCap,
  "144": School,
  "146": School,

  // Artes e Humanidades
  "210": Palette,
  "211": Paintbrush,
  "212": Music,
  "213": Film,
  "214": PenTool,
  "215": Scissors,
  "222": Globe,
  "223": BookOpen,
  "225": Landmark,
  "226": Brain,
  "229": BookOpen,

  // Ciências Sociais, Jornalismo, Empresariais e Direito
  "310": Users,
  "311": Brain,
  "312": Users,
  "313": Landmark,
  "314": TrendingUp,
  "319": Users,
  "320": Newspaper,
  "321": Newspaper,
  "322": Library,
  "340": Briefcase,
  "342": Megaphone,
  "343": Banknote,
  "344": Calculator,
  "345": Building2,
  "346": FileText,
  "347": Briefcase,
  "349": Briefcase,
  "380": Scale,

  // Ciências, Matemática e Informática
  "420": Leaf,
  "421": Dna,
  "422": Leaf,
  "441": Atom,
  "442": FlaskConical,
  "443": Globe,
  "460": Calculator,
  "461": Calculator,
  "462": BarChart2,
  "480": Monitor,
  "481": Code,

  // Engenharia e Indústria
  "520": Wrench,
  "521": Hammer,
  "522": Zap,
  "523": Cpu,
  "524": FlaskConical,
  "525": Car,
  "529": Wrench,
  "541": UtensilsCrossed,
  "542": Shirt,
  "543": Package,
  "544": Mountain,
  "581": Building,
  "582": HardHat,

  // Agricultura e Veterinária
  "620": Wheat,
  "621": Wheat,
  "622": Flower2,
  "623": TreePine,
  "640": PawPrint,

  // Saúde
  "720": HeartPulse,
  "721": Stethoscope,
  "723": HeartHandshake,
  "724": Smile,
  "725": Microscope,
  "726": HeartHandshake,
  "727": Pill,
  "729": HeartPulse,

  // Serviços
  "762": Users,
  "811": UtensilsCrossed,
  "812": Map,
  "813": Dumbbell,
  "840": Truck,
  "851": Leaf,
  "852": TreePine,
  "853": HeartPulse,
  "861": Shield,
  "862": ShieldCheck,
  "863": Shield,

  "999": HelpCircle,
};
