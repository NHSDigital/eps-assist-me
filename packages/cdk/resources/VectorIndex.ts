import {Construct} from "constructs"
import {Duration} from "aws-cdk-lib"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import {CfnCollection} from "aws-cdk-lib/aws-opensearchserverless"
import {AwsCustomResource, PhysicalResourceId, AwsCustomResourcePolicy} from "aws-cdk-lib/custom-resources"
import {LambdaFunction} from "../constructs/LambdaFunction"

export interface VectorIndexProps {
  indexName: string
  collection: CfnCollection
  createIndexFunction: LambdaFunction
  endpoint: string
}

export class VectorIndex extends Construct {
  public readonly vectorIndex: AwsCustomResource

  constructor(scope: Construct, id: string, props: VectorIndexProps) {
    super(scope, id)

    // Custom resource to manage OpenSearch vector index lifecycle via Lambda
    this.vectorIndex = new AwsCustomResource(this, "VectorIndex", {
      installLatestAwsSdk: true,
      // Create index when stack is deployed
      onCreate: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: props.createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Create",
            CollectionName: props.collection.name,
            IndexName: props.indexName,
            Endpoint: props.endpoint
          })
        },
        physicalResourceId: PhysicalResourceId.of(`VectorIndex-${props.indexName}`)
      },
      // Delete index when stack is destroyed
      onDelete: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: props.createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Delete",
            CollectionName: props.collection.name,
            IndexName: props.indexName,
            Endpoint: props.endpoint
          })
        }
      },
      // Grant permission to invoke the Lambda function
      policy: AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [props.createIndexFunction.function.functionArn]
        })
      ]),
      timeout: Duration.seconds(60)
    })

    // Ensure collection exists before creating index
    this.vectorIndex.node.addDependency(props.collection)
  }
}
