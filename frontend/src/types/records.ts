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

export type ApiFieldErrors = Record<string, string>