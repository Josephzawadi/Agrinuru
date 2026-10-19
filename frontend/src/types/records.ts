export interface FarmerProfile {
  id: number
  full_name: string
  phone_number: string
  email: string
  county: string
  sub_county: string
  preferred_language: string
  date_registered: string
}

export interface FarmerInput {
  full_name: string
  phone_number: string
  email: string
  county: string
  sub_county: string
  preferred_language: string
}

export interface Farm {
  id: number
  farmer: number
  farm_name: string
  location: string
  approximate_size_acres: string
  date_created: string
}

export interface FarmInput {
  farmer: number
  farm_name: string
  location: string
  approximate_size_acres: string
}

export const cropGrowthStages = [
  'planned',
  'planted',
  'germinating',
  'vegetative',
  'flowering',
  'fruiting',
  'maturing',
  'harvested',
] as const

export type CropGrowthStage = (typeof cropGrowthStages)[number]
export type HarvestQuantityUnit = 'kg' | 'tonne'

export interface Crop {
  id: number
  crop_name: string
  variety: string
  farm: number
  farm_name: string
  planting_date: string
  expected_harvest_date: string
  cultivated_area_acres: string
  growth_stage: CropGrowthStage
  expected_harvest_quantity: string | null
  harvest_quantity_unit: HarvestQuantityUnit | ''
  created_at: string
  updated_at: string
}

export interface CropInput {
  crop_name: string
  variety: string
  farm: number
  planting_date: string
  expected_harvest_date: string
  cultivated_area_acres: string
  growth_stage: CropGrowthStage
  expected_harvest_quantity: string | null
  harvest_quantity_unit: HarvestQuantityUnit | ''
}

export type ProductionActivityType =
  | 'planting'
  | 'weeding'
  | 'irrigation'
  | 'fertilizer_application'
  | 'pest_control'
  | 'pruning'
  | 'soil_preparation'
  | 'scouting'
  | 'other'

export type ProductionInputType = 'seed' | 'fertilizer' | 'pesticide' | 'herbicide' | 'other'
export type ProductionInputUnit = 'g' | 'kg' | 'tonne' | 'ml' | 'l' | 'piece' | 'packet' | 'bag'
export type ExpenseCategory = 'labour' | 'land_preparation' | 'irrigation' | 'machinery' | 'transport' | 'storage' | 'other'
export type CurrencyCode = string

export interface ProductionRecordContext {
  id: number
  crop: number
  crop_name: string
  farm_id: number
  farm_name: string
  farmer_id: number
  farmer_name: string
  created_at: string
  updated_at: string
  voided_at: string | null
  void_reason: string
  is_voided: boolean
}

export interface ProductionActivity extends ProductionRecordContext {
  activity_type: ProductionActivityType
  activity_date: string
  description: string
  notes: string
}

export interface ProductionActivityInput {
  crop: number
  activity_type: ProductionActivityType
  activity_date: string
  description: string
  notes: string
}

export interface InputUsage extends ProductionRecordContext {
  input_type: ProductionInputType
  product_name: string
  usage_date: string
  quantity: string
  quantity_unit: ProductionInputUnit
  purchase_cost: string | null
  currency_code: CurrencyCode
  notes: string
}

export interface InputUsageInput {
  crop: number
  input_type: ProductionInputType
  product_name: string
  usage_date: string
  quantity: string
  quantity_unit: ProductionInputUnit
  purchase_cost: string | null
  currency_code: CurrencyCode
  notes: string
}

export interface ProductionExpense extends ProductionRecordContext {
  category: ExpenseCategory
  description: string
  expense_date: string
  amount: string
  currency_code: CurrencyCode
  notes: string
}

export interface ProductionExpenseInput {
  crop: number
  category: ExpenseCategory
  description: string
  expense_date: string
  amount: string
  currency_code: CurrencyCode
  notes: string
}

export interface HarvestRecord extends ProductionRecordContext {
  harvest_date: string
  quantity: string
  quantity_unit: HarvestQuantityUnit
  notes: string
}

export interface HarvestRecordInput {
  crop: number
  harvest_date: string
  quantity: string
  quantity_unit: HarvestQuantityUnit
  notes: string
}

export interface ProductionFilters {
  crop?: number
  farm?: number
  farmer?: number
  date_from?: string
  date_to?: string
  include_voided?: boolean
}

export interface ProductionCropSummary {
  crop_id: number
  crop_name: string
  variety: string
  farm_id: number
  farm_name: string
  farmer_id: number
  farmer_name: string
  expected_harvest: {
    quantity: string | null
    unit: HarvestQuantityUnit | null
    normalized_kg: string | null
  }
  actual_harvest: {
    quantity_by_unit: Partial<Record<HarvestQuantityUnit, string>>
    normalized_kg: string | null
    record_count: number
  }
  comparison: {
    status: 'comparable' | 'period_limited' | 'no_harvest_recorded' | 'expected_not_recorded_or_unit_incompatible'
    unit: 'kg' | null
    difference_kg: string | null
  }
  input_usage_by_type_product_unit: Array<{
    input_type: ProductionInputType
    product_name: string
    quantity_unit: ProductionInputUnit
    quantity: string
  }>
  record_counts: {
    activities: number
    input_usages: number
    expenses: number
    harvests: number
  }
}

export interface ProductionCostSummary {
  currency_code: CurrencyCode
  input_purchases: string
  other_expenses: string
  total: string
}

export interface ProductionSummary {
  filters: Omit<ProductionFilters, 'include_voided'>
  harvest_comparison_scope: 'selected_period_only' | 'full_recorded_season'
  crops: ProductionCropSummary[]
  active_record_counts: {
    activities: number
    input_usages: number
    expenses: number
    harvests: number
  }
  costs_by_currency: ProductionCostSummary[]
}

export type ApiFieldErrors = Record<string, string>