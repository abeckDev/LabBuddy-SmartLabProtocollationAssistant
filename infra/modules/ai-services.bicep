param location string
param resourceToken string
param tags object

@description('OpenAI model to deploy for the extraction agent')
param openaiModelName string = 'gpt-4o'

@description('OpenAI model version')
param openaiModelVersion string = '2024-11-20'

@description('Deployment name for the extraction agent model')
param openaiDeploymentName string = 'gpt-4o'

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'ai-${resourceToken}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: 'labbuddy-${resourceToken}'
    publicNetworkAccess: 'Enabled'
  }
}

// Deploy an OpenAI model for the extraction agent
resource extractionModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServices
  name: openaiDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: openaiModelName
      version: openaiModelVersion
    }
  }
}

output endpoint string = aiServices.properties.endpoint
output accountName string = aiServices.name
output openaiDeploymentName string = extractionModel.name
