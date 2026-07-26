declare namespace API {
  type Repository = {
    created_at: string
    file_name: string
    updated_at: string
    user_id: string
    paper_title?: string
    authors?: string
    journal?: string
    publication_year?: number
    file_type?: string
    extraction_status?: string
  }
}
