import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {CfnKnowledgeBase, CfnDataSource} from "aws-cdk-lib/aws-bedrock"
import {
  ChunkingStrategy,
  ContentFilterStrength,
  ContentFilterType,
  Guardrail,
  GuardrailAction,
  ManagedWordFilterType,
  PIIType
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {Fn, RemovalPolicy} from "aws-cdk-lib"
import {
  LogGroup,
  RetentionDays,
  CfnDeliverySource,
  CfnDeliveryDestination,
  CfnDelivery,
  CfnLogGroup
} from "aws-cdk-lib/aws-logs"
import {Key} from "aws-cdk-lib/aws-kms"

// Amazon Titan embedding model for vector generation
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export interface VectorKnowledgeBaseProps {
  readonly stackName: string
  readonly docsBucket: Bucket
  readonly bedrockExecutionRole: Role
  readonly collectionArn: string
  readonly vectorIndexName: string
  readonly region: string
  readonly account: string
  readonly logRetentionInDays: number
}

export class VectorKnowledgeBaseResources extends Construct {
  public readonly knowledgeBase: CfnKnowledgeBase
  public readonly guardrail: Guardrail
  public readonly dataSource: CfnDataSource
  public readonly kbLogGroup: LogGroup
  private readonly region: string
  private readonly account: string

  public get dataSourceArn(): string {
    return `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/` +
      `${this.knowledgeBase.attrKnowledgeBaseId}/data-source/` +
      `${this.dataSource.attrDataSourceId}`
  }

  cloudWatchLogsKmsKey = Key.fromKeyArn(
    this, "cloudWatchLogsKmsKey", Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn"))

  constructor(scope: Construct, id: string, props: VectorKnowledgeBaseProps) {
    super(scope, id)

    this.region = props.region
    this.account = props.account

    const guardrail = new Guardrail(this, "bedrockGuardrails", {
      name: `${props.stackName}-guardrail`,
      description: "Guardrail for EPS Assist Me Slackbot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentFilters: [
        {
          type: ContentFilterType.SEXUAL,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.VIOLENCE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.HATE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.INSULTS,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.MISCONDUCT,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.PROMPT_ATTACK,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.NONE
        }
      ],
      piiFilters: [
        {
          type: PIIType.General.EMAIL,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.PHONE,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.NAME,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.Finance.CREDIT_DEBIT_CARD_NUMBER,
          action: GuardrailAction.BLOCK
        },
        {
          type: PIIType.UKSpecific.UK_NATIONAL_HEALTH_SERVICE_NUMBER,
          action: GuardrailAction.ANONYMIZE
        }
      ],
      managedWordListFilters: [
        {type: ManagedWordFilterType.PROFANITY}
      ]
    })

    // Create vector knowledge base for document retrieval
    const knowledgeBase = new CfnKnowledgeBase(this, "VectorKB", {
      name: `${props.stackName}-kb`,
      description: "Knowledge base for EPS Assist Me Slackbot",
      roleArn: props.bedrockExecutionRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:eu-west-2::foundation-model/${EMBEDDING_MODEL}`
        }
      },
      // Configure OpenSearch Serverless as vector store
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: props.collectionArn,
          vectorIndexName: props.vectorIndexName,
          // Standard Bedrock field mappings for vector search
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          }
        }
      }
    })

    knowledgeBase.applyRemovalPolicy(RemovalPolicy.DESTROY)

    const chunkingStrategyConfiguration = {
      ...ChunkingStrategy.SEMANTIC.configuration,
      // hierarchicalChunkingConfiguration: {
      //   levelConfigurations: [
      //     {maxTokens: 1000},
      //     {maxTokens: 400}
      //   ],
      //   overlapTokens: 150
      // }
      semanticChunkingConfiguration: {
        breakpointPercentileThreshold: 60,
        bufferSize: 1,
        maxTokens: 300
      }
    }

    let chunkingStrategyId = chunkingStrategyConfiguration === ChunkingStrategy.NONE.configuration
      ? "default"
      : chunkingStrategyConfiguration.chunkingStrategy.replace("_", "-").toLocaleLowerCase()

    // Create S3 data source for knowledge base documents
    // prefix pointed to processed/ to only ingest converted markdown documents
    const dataSource = new CfnDataSource(this, "S3DataSource", {
      knowledgeBaseId: knowledgeBase.attrKnowledgeBaseId,
      name: `${props.stackName}-s3-datasource-${chunkingStrategyId}`,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: props.docsBucket.bucketArn,
          inclusionPrefixes: ["processed/"]
        }
      },
      vectorIngestionConfiguration: {
        chunkingConfiguration: chunkingStrategyConfiguration
      }
    })

    // Configure CloudWatch Logs delivery for Knowledge Base logging
    // Create log group for KB application logs
    const kbLogGroup = new LogGroup(this, "KBApplicationLogGroup", {
      encryptionKey: this.cloudWatchLogsKmsKey,
      logGroupName: `/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/${knowledgeBase.attrKnowledgeBaseId}`,
      retention: props.logRetentionInDays as RetentionDays,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Suppress CFN guard rules for log group
    const cfnlogGroup = kbLogGroup.node.defaultChild as CfnLogGroup
    cfnlogGroup.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "CW_LOGGROUP_RETENTION_PERIOD_CHECK"
        ]
      }
    }

    // Create delivery source for the Knowledge Base
    const kbDeliverySource = new CfnDeliverySource(this, "KBDeliverySource", {
      name: `${props.stackName}-kb-delivery-source`,
      logType: "APPLICATION_LOGS",
      resourceArn: knowledgeBase.attrKnowledgeBaseArn
    })

    // Create delivery destination pointing to the log group
    const kbDeliveryDestination = new CfnDeliveryDestination(this, "KBDeliveryDestination", {
      name: `${props.stackName}-kb-delivery-destination`,
      destinationResourceArn: kbLogGroup.logGroupArn
    })

    // Create delivery to link source and destination
    const kbDelivery = new CfnDelivery(this, "KBDelivery", {
      deliverySourceName: kbDeliverySource.name,
      deliveryDestinationArn: kbDeliveryDestination.attrArn
    })

    // Ensure proper resource dependencies
    kbDeliverySource.node.addDependency(knowledgeBase)
    kbDelivery.node.addDependency(kbDeliverySource)
    kbDelivery.node.addDependency(kbDeliveryDestination)

    this.knowledgeBase = knowledgeBase
    this.dataSource = dataSource
    this.guardrail = guardrail
    this.kbLogGroup = kbLogGroup
  }
}
