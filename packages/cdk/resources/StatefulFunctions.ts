import {Construct} from "constructs"
import {PythonLambdaFunction} from "@nhsdigital/eps-cdk-constructs"
import {ManagedPolicy} from "aws-cdk-lib/aws-iam"
import {resolve} from "path"

export interface StatefulFunctionsProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly logRetentionInDays: number
  readonly logLevel: string
  readonly syncKnowledgeBaseManagedPolicy: ManagedPolicy
  readonly preprocessingManagedPolicy: ManagedPolicy
  readonly knowledgeBaseId: string
  readonly dataSourceId: string
  readonly region: string
  readonly account: string
  readonly docsBucketName: string
}

export class StatefulFunctions extends Construct {
  public readonly syncKnowledgeBaseFunction: PythonLambdaFunction
  public readonly preprocessingFunction: PythonLambdaFunction

  constructor(scope: Construct, id: string, props: StatefulFunctionsProps) {
    super(scope, id)

    // Lambda function to preprocess documents (convert to markdown)
    const preprocessingFunction = new PythonLambdaFunction(this, "PreprocessingFunction", {
      functionName: `${props.stackName}-PreprocessingFunction`,
      projectBaseDir: resolve(__dirname, "../../.."),
      packageBasePath: "packages/preprocessingFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/preprocessingFunction",
      environmentVariables: {
        "DOCS_BUCKET_NAME": props.docsBucketName,
        "RAW_PREFIX": "raw/",
        "PROCESSED_PREFIX": "processed/",
        "AWS_ACCOUNT_ID": props.account
      },
      additionalPolicies: [props.preprocessingManagedPolicy]
    })

    // Lambda function to sync knowledge base on S3 events
    const syncKnowledgeBaseFunction = new PythonLambdaFunction(this, "SyncKnowledgeBaseFunction", {
      functionName: `${props.stackName}-SyncKnowledgeBaseFunction`,
      projectBaseDir: resolve(__dirname, "../../.."),
      packageBasePath: "packages/syncKnowledgeBaseFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/syncKnowledgeBaseFunction",
      environmentVariables: {
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "DATA_SOURCE_ID": props.dataSourceId
      },
      additionalPolicies: [props.syncKnowledgeBaseManagedPolicy]
    })

    this.preprocessingFunction = preprocessingFunction
    this.syncKnowledgeBaseFunction = syncKnowledgeBaseFunction
  }
}
