declare namespace API {
  interface Session {
    created_at: string
    session_id: string
    session_name: string
    updated_at: string
    // user_id: string
  }

  interface ChatItem {
    id: number
    role: import('@/configs').ChatRole
    type: import('@/configs').ChatType
    loading?: boolean
    error?: string
    content?: string
    think?: string

    documents?: Document[]
    reference?: Reference[]
    recommended_questions?: string[]
    prediction_result?: PredictionResult
    image_results?: {
      images?: {
        title: string
        imageUrl: string
        thumbnailUrl: string
        source: string
        link: string
        googleUrl: string
      }[]
    }
    video_results?: {
      videos?: {
        title: string
        link: string
        imageUrl: string
      }[]
    }
  }

  interface Document {
    document_id: string
    document_name: string
    content_with_weight: string
  }

  interface Reference {
    document_id?: number | string
    document_name?: string
    content_with_weight?: string
    url?: string
    _source?: 'knowledge_base' | 'web_search' | 'attachment'
  }

  // EGC 领域新增类型

  interface MixDesign {
    binder_type?: string
    fly_ash_ratio?: number
    slag_ratio?: number
    metakaolin_ratio?: number
    water_binder_ratio?: number
    sand_binder_ratio?: number
    alkaline_activator_type?: string
    naoh_molarity?: number
    na2sio3_naoh_ratio?: number
    activator_modulus?: number
    fiber_type?: string
    fiber_content_vol?: number
    fiber_length?: number
    fiber_diameter?: number
    fiber_tensile_strength?: number
    fiber_elastic_modulus?: number
    curing_age_days?: number
    curing_temperature?: number
    curing_method?: string
  }

  interface PropertyPrediction {
    value?: number
    range_low?: number
    range_high?: number
    confidence?: number
    unit?: string
    key_factors?: string[]
  }

  interface PredictionResult {
    status: string
    message: string
    predictions?: {
      compressive_strength?: PropertyPrediction
      ultimate_tensile_strain?: PropertyPrediction
      flexural_strength?: PropertyPrediction
      elastic_modulus?: PropertyPrediction
      tensile_strength?: PropertyPrediction
      fracture_energy?: PropertyPrediction
    }
    strain_hardening_analysis?: {
      expected: boolean
      reasoning: string
      expected_crack_pattern: string
    }
    key_findings?: string
    limitations?: string
    similar_data_count?: number
    references_count?: number
  }

  interface OptimizationTarget {
    compressive_strength_min?: number
    compressive_strength_max?: number
    ultimate_tensile_strain_min?: number
    ultimate_tensile_strain_max?: number
    flexural_strength_min?: number
    flexural_strength_max?: number
    elastic_modulus_min?: number
  }

  interface OptimizationSuggestion {
    parameter: string
    suggested_range: string
    recommended_value?: number
    rationale: string
    expected_effect?: string
    confidence?: number
  }

  interface OptimizationResult {
    status: string
    message: string
    suggestions?: OptimizationSuggestion[]
    best_guess_mix?: MixDesign
    expected_properties?: Record<string, { value: number; range: string }>
    trade_offs?: string
    implementation_notes?: string
  }

  interface ExperimentalDataRow {
    id: number
    kb_id?: number
    file_name?: string
    binder_type?: string
    fly_ash_ratio?: number
    slag_ratio?: number
    water_binder_ratio?: number
    fiber_type?: string
    fiber_content_vol?: number
    compressive_strength_mpa?: number
    ultimate_tensile_strain_pct?: number
    flexural_strength_mpa?: number
    elastic_modulus_gpa?: number
    curing_age_days?: number
    curing_temperature?: number
    curing_method?: string
    test_method?: string
    confidence_score?: number
    created_at?: string
  }
}
