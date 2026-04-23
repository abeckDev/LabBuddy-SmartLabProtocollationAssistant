targetScope = 'subscription'

@description('Primary location for all resources')
param location string

@description('Name of the environment (e.g., dev, prod)')
param environmentName string

@description('Container image to deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Voice Live model to use')
param voiceLiveModel string = 'gpt-4o'

@description('TTS voice name')
param voiceLiveVoice string = 'de-DE-SeraphinaMultilingualNeural'

@description('OpenAI model name to deploy for extraction agent')
param openaiModelName string = 'gpt-4o'

@description('OpenAI model version')
param openaiModelVersion string = '2024-11-20'

var resourceToken = toLower(uniqueString(subscription().subscriptionId, environmentName, location))
var tags = { 'azd-env-name': environmentName, project: 'labbuddy' }
var rgName = 'rg-labbuddy-${environmentName}'

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: rgName
  location: location
  tags: tags
}

// Container Apps Environment + Log Analytics
module containerEnv 'modules/container-env.bicep' = {
  name: 'container-env'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Azure AI Services (Voice Live)
module aiServices 'modules/ai-services.bicep' = {
  name: 'ai-services'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
    openaiModelName: openaiModelName
    openaiModelVersion: openaiModelVersion
  }
}

// Storage Account (conversation artifacts)
module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Azure Container Registry
module acr 'modules/container-registry.bicep' = {
  name: 'container-registry'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Container App
module containerApp 'modules/container-app.bicep' = {
  name: 'container-app'
  scope: rg
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
    containerImage: containerImage
    environmentId: containerEnv.outputs.environmentId
    voiceLiveEndpoint: aiServices.outputs.endpoint
    storageEndpoint: storage.outputs.endpoint
    voiceLiveModel: voiceLiveModel
    voiceLiveVoice: voiceLiveVoice
    openaiEndpoint: aiServices.outputs.endpoint
    openaiDeployment: aiServices.outputs.openaiDeploymentName
    acrLoginServer: acr.outputs.loginServer
    acrName: acr.outputs.name
  }
}

// Role assignments: Container App MI → AI Services + Storage
module roles 'modules/role-assignments.bicep' = {
  name: 'role-assignments'
  scope: rg
  params: {
    principalId: containerApp.outputs.identityPrincipalId
    aiServicesName: aiServices.outputs.accountName
    storageAccountName: storage.outputs.accountName
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_APP_URL string = containerApp.outputs.fqdn
output AZURE_VOICELIVE_ENDPOINT string = aiServices.outputs.endpoint
output AZURE_STORAGE_ENDPOINT string = storage.outputs.endpoint
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = acr.outputs.name
