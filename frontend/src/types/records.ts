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

export type ApiFieldErrors = Record<string, string>